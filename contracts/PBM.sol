// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PBM (Purpose Bound Money) for Tokyo Subsidy
 * @notice JPYC をラップして「目的」を付与するシンプルな PBM 実装の参考。
 *         本 MVP のオフチェーン実装 (`backend/app/services/pbm.py`) は
 *         本コントラクトと同じステートマシンを SQLite 上で再現している。
 */

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract PBM {
    // ---- データ構造 ----

    struct Program {
        bytes32 id;
        address issuer;          // 東京都トレジャリー
        uint256 budget;          // ロック済み JPYC
        uint256 spent;
        uint64  startAt;
        uint64  endAt;
        uint16  subsidyBps;      // 助成率 (basis points: 3000 = 30%)
        uint256 perCitizenCap;   // 住民ごとの累計上限
        bool    revoked;
    }

    struct Allowance {
        bytes32 programId;
        uint256 used;
    }

    IERC20  public immutable jpyc;
    address public governor;     // 東京都の管理アドレス

    mapping(bytes32 => Program) public programs;
    mapping(bytes32 => mapping(bytes13 => bool)) public eligibleJans;     // programId => JAN(13) => bool
    mapping(bytes32 => mapping(address => bool)) public approvedStores;   // programId => store => bool
    mapping(bytes32 => mapping(bytes32 => bool)) public eligibleCitizens; // programId => citizenPid => bool
    mapping(bytes32 => Allowance) public allowances;                      // pid => allowance

    // ---- イベント (EBPM 用) ----

    event ProgramCreated(bytes32 indexed programId, uint256 budget, uint64 startAt, uint64 endAt);
    event PBMIssued(bytes32 indexed programId, bytes32 indexed citizenPid);
    event Spent(
        bytes32 indexed programId,
        bytes32 indexed citizenPid,
        address indexed store,
        bytes13 jan,
        uint256 totalJpy,
        uint256 subsidyJpy
    );
    event ProgramRevoked(bytes32 indexed programId);

    modifier onlyGovernor() {
        require(msg.sender == governor, "PBM: not governor");
        _;
    }

    constructor(address jpyc_) {
        jpyc = IERC20(jpyc_);
        governor = msg.sender;
    }

    // ---- 東京都オペレーション ----

    function createProgram(
        bytes32 id,
        uint256 budget,
        uint64  startAt,
        uint64  endAt,
        uint16  subsidyBps,
        uint256 perCitizenCap
    ) external onlyGovernor {
        require(programs[id].issuer == address(0), "PBM: id used");
        require(endAt > startAt, "PBM: bad period");
        require(subsidyBps <= 10_000, "PBM: bad bps");

        require(jpyc.transferFrom(msg.sender, address(this), budget), "PBM: deposit fail");

        programs[id] = Program({
            id: id,
            issuer: msg.sender,
            budget: budget,
            spent: 0,
            startAt: startAt,
            endAt: endAt,
            subsidyBps: subsidyBps,
            perCitizenCap: perCitizenCap,
            revoked: false
        });

        emit ProgramCreated(id, budget, startAt, endAt);
    }

    function setEligibleJans(bytes32 programId, bytes13[] calldata jans, bool ok) external onlyGovernor {
        for (uint256 i = 0; i < jans.length; i++) {
            eligibleJans[programId][jans[i]] = ok;
        }
    }

    function setApprovedStores(bytes32 programId, address[] calldata stores, bool ok) external onlyGovernor {
        for (uint256 i = 0; i < stores.length; i++) {
            approvedStores[programId][stores[i]] = ok;
        }
    }

    /// @notice 自治体システムが eligibility 確認後にコール
    function issueTo(bytes32 programId, bytes32 citizenPid) external onlyGovernor {
        Program storage p = programs[programId];
        require(p.issuer != address(0) && !p.revoked, "PBM: no program");
        eligibleCitizens[programId][citizenPid] = true;
        emit PBMIssued(programId, citizenPid);
    }

    function revokeProgram(bytes32 programId) external onlyGovernor {
        Program storage p = programs[programId];
        require(p.issuer != address(0), "PBM: no program");
        p.revoked = true;
        uint256 refund = p.budget - p.spent;
        if (refund > 0) {
            require(jpyc.transfer(p.issuer, refund), "PBM: refund fail");
        }
        emit ProgramRevoked(programId);
    }

    // ---- 加盟店 POS が呼ぶ決済 ----

    /// @param programId    どの助成プログラムか
    /// @param citizenPid   住民の擬似 ID (HMAC)
    /// @param jan          商品 JAN (13 byte)
    /// @param totalJpy     購入総額
    /// @return subsidyJpy  実際に出た助成金額
    function spend(
        bytes32 programId,
        bytes32 citizenPid,
        bytes13 jan,
        uint256 totalJpy
    ) external returns (uint256 subsidyJpy) {
        Program storage p = programs[programId];
        require(p.issuer != address(0) && !p.revoked, "PBM: no program");
        require(block.timestamp >= p.startAt && block.timestamp <= p.endAt, "PBM: out of period");
        require(approvedStores[programId][msg.sender], "PBM: store not approved");
        require(eligibleJans[programId][jan], "PBM: jan not eligible");
        require(eligibleCitizens[programId][citizenPid], "PBM: citizen not eligible");

        subsidyJpy = (totalJpy * p.subsidyBps) / 10_000;

        // 個別上限
        Allowance storage al = allowances[citizenPid];
        if (al.programId != programId) {
            al.programId = programId;
            al.used = 0;
        }
        if (al.used + subsidyJpy > p.perCitizenCap) {
            subsidyJpy = p.perCitizenCap - al.used;
        }

        // 予算
        if (p.spent + subsidyJpy > p.budget) {
            subsidyJpy = p.budget - p.spent;
        }
        require(subsidyJpy > 0, "PBM: cap exhausted");

        al.used += subsidyJpy;
        p.spent += subsidyJpy;

        require(jpyc.transfer(msg.sender, subsidyJpy), "PBM: payout fail");

        emit Spent(programId, citizenPid, msg.sender, jan, totalJpy, subsidyJpy);
    }
}
