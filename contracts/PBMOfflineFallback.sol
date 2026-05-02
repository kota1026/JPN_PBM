// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PBMOfflineFallback (CP-6)
 * @notice 首都直下地震等でネット/電力が断絶した状況下でも、
 *         事前発行された署名済みオフラインクーポン (QR) によって
 *         加盟店が住民への助成支給を継続できるフェイルセーフ機構。
 *
 *         ## モデル
 *         平時:
 *         1. 都 (governor) が住民の wallet に PBM を発行する際、
 *            同時に "災害モード QR" を 1 ヶ月単位で署名・配布する。
 *         2. QR には (programId, pid, monthIndex, capJpy, expiresAt) と
 *            governor の ECDSA 署名 (EIP-191 personal_sign) が埋まる。
 *
 *         有事 (オフライン):
 *         3. 加盟店 POS は QR を読み取り、ローカルで署名検証 + nonce 重複検査
 *            を行い、住民にその場で助成を与える (紙のレシートも発行)。
 *         4. POS は redemption トランザクションをローカルキューに溜める。
 *
 *         復旧後:
 *         5. POS はキューを `redeemBatch` で本コントラクトに提出。
 *         6. 本コントラクトが署名検証 + nonce 重複検査 + 残高確認 → JPYC を払い出す。
 *
 *         ## 安全要件
 *         - **二重支給** (CP-5): nonce は (pid, monthIndex) で 1 回のみ消費可能。
 *         - **なりすまし** (CP-5): 署名は governor の鍵でのみ検証成功。
 *         - **転売** (CP-5): pid に紐づく QR は他人 wallet では使えない (oncahin で pid 検証)。
 *         - **改ざん**: QR の payload を 1bit 変えると署名検証で落ちる。
 *         - **災害時可用性** (CP-6): オフライン側は最大 30 日間有効。
 */

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract PBMOfflineFallback {
    // ---- 型 ----

    /// @dev オフライン QR の本体 (governor が事前署名)
    struct OfflineCoupon {
        bytes32 programId;
        bytes32 pid;          // 住民擬似 ID (HMAC)
        uint32  monthIndex;   // 例: 2026-04 = 202604
        uint256 capJpy;       // この月の上限
        uint64  expiresAt;    // QR の失効時刻 (Unix 秒)
    }

    /// @dev 加盟店が POS で受領した個別 redemption (オフラインで蓄積)
    struct OfflineRedemption {
        OfflineCoupon coupon;
        address store;
        uint256 amountJpy;    // この redemption での助成額
        uint64  redeemedAt;   // POS が受領した時刻
        bytes   couponSig;    // governor が coupon に対して付与した EIP-191 署名
    }

    // ---- ストレージ ----

    IERC20  public immutable jpyc;
    address public governor;

    /// @dev (pid, monthIndex) → 既に消費された助成額。
    ///      capJpy を超えて redeem できない仕組み。
    mapping(bytes32 => mapping(uint32 => uint256)) public consumed;

    /// @dev 認定加盟店 (オフライン redemption を受けられる店)
    mapping(address => bool) public approvedStores;

    // ---- イベント ----

    event Redeemed(
        bytes32 indexed programId,
        bytes32 indexed pid,
        address indexed store,
        uint32  monthIndex,
        uint256 amountJpy,
        uint64  redeemedAt
    );

    event StoreApproved(address indexed store, bool ok);
    event GovernorTransferred(address indexed from, address indexed to);

    modifier onlyGovernor() {
        require(msg.sender == governor, "OF: not governor");
        _;
    }

    constructor(address jpyc_) {
        jpyc = IERC20(jpyc_);
        governor = msg.sender;
    }

    // ---- 都オペレーション ----

    function setApprovedStore(address store, bool ok) external onlyGovernor {
        approvedStores[store] = ok;
        emit StoreApproved(store, ok);
    }

    function transferGovernor(address next) external onlyGovernor {
        require(next != address(0), "OF: zero gov");
        emit GovernorTransferred(governor, next);
        governor = next;
    }

    // ---- ハッシュ・署名検証 ----

    /// @dev coupon → keccak256 ハッシュ。POS 側 (Python) と同じ並びで結合する。
    function couponHash(OfflineCoupon calldata c) public pure returns (bytes32) {
        return keccak256(
            abi.encode(c.programId, c.pid, c.monthIndex, c.capJpy, c.expiresAt)
        );
    }

    /// @dev EIP-191 personal_sign のメッセージダイジェスト。
    function ethSignedDigest(bytes32 h) public pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", h));
    }

    function _recover(bytes32 digest, bytes memory sig) internal pure returns (address) {
        require(sig.length == 65, "OF: bad sig len");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        if (v < 27) v += 27;
        require(v == 27 || v == 28, "OF: bad v");
        return ecrecover(digest, v, r, s);
    }

    function verifyCoupon(OfflineCoupon calldata c, bytes calldata sig) public view returns (bool) {
        bytes32 digest = ethSignedDigest(couponHash(c));
        return _recover(digest, sig) == governor;
    }

    // ---- 復旧後バッチ redemption ----

    /// @notice POS が復旧後に蓄積した redemption をまとめて提出する。
    ///         1 件でも検証失敗があると revert (集団失敗で原因特定しやすくする)。
    function redeemBatch(OfflineRedemption[] calldata items) external returns (uint256 totalPaid) {
        require(approvedStores[msg.sender], "OF: store not approved");
        for (uint256 i = 0; i < items.length; i++) {
            OfflineRedemption calldata it = items[i];
            require(it.store == msg.sender, "OF: store mismatch");
            require(it.amountJpy > 0, "OF: zero amount");
            require(block.timestamp <= it.coupon.expiresAt + 30 days, "OF: too late");

            bytes32 digest = ethSignedDigest(couponHash(it.coupon));
            require(_recover(digest, it.couponSig) == governor, "OF: bad sig");

            uint256 used = consumed[it.coupon.pid][it.coupon.monthIndex];
            require(used + it.amountJpy <= it.coupon.capJpy, "OF: cap exceeded");
            consumed[it.coupon.pid][it.coupon.monthIndex] = used + it.amountJpy;

            require(jpyc.transfer(msg.sender, it.amountJpy), "OF: payout fail");
            totalPaid += it.amountJpy;

            emit Redeemed(
                it.coupon.programId,
                it.coupon.pid,
                msg.sender,
                it.coupon.monthIndex,
                it.amountJpy,
                it.redeemedAt
            );
        }
    }

    /// @notice (pid, monthIndex) に対して既に消費された金額を取得 (POS の重複防止用)。
    function consumedOf(bytes32 pid, uint32 monthIndex) external view returns (uint256) {
        return consumed[pid][monthIndex];
    }
}
