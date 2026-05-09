# 戦略会議 #14 — 外部依存を待つ前のラスト 1 マイル (Round 15)

> **作成日**: 2026-05-09 (round 15)
> **議題**: Round 14 で「中身 + 動かせる + 送れる」が揃った。Round 15 では実 RPC / 実 GCash / 実 iPhone / 実 DSWD 連携が手に入った瞬間に **スイッチ 1 つで切替えられる** よう、すべてのアダプタ層・モック・仕様書を整備する。
> **アウトプット**: 6 件採択 + 戦略文書英訳 1 本

---

## 0. 動機 ─ なぜ「アダプタ層」を先に書くのか

Round 14 までの実装は backend の純粋関数 + Python in-process mock で完結していた。
本物に切替える時に何が起きるか:

| 領域 | 現状 (R14) | 本物への移行 | リスク |
|------|-----------|-------------|------|
| ブロックチェーン | Python `sol_simulator.py` が EVM 模倣 | Polygon Mumbai → web3.py 経由で本物の RPC を叩く | RPC 不安定、署名形式の差、gas 切れ |
| GCash 決済 | フロントの mock UUID | GCash Sandbox API → 実 HTTPS 呼び出し | API rate limit、エラーハンドリング |
| iPhone scanner | デスクトップ Chrome で動作確認 | 実 iPhone の Safari (iOS 17+) で BarcodeDetector or ZXing | iOS BarcodeDetector が EAN-13 未対応バージョン |
| 個人 ID 連携 | PhilSys mock OAuth | 実 PhilSys API + LandBank ATM カード連携 | PSN 形式変換、4Ps 名簿照合 |
| JICA 申請 | v1 ドラフト英文 | プリスクリーン会話 → v2 改訂 | LoI 揃わない / 予算根拠不足 |

**アダプタ層を先に書く** = 切替 1 行 (env var or DI) で、本物に置換可能な状態にしておく。
これにより「外部資源が手に入った日 = production 投入できる日」になる。

## 1. 採択 6 件 (1〜6 を並列実装)

| # | エージェント | 提案 | 実装 | 影響 |
|---|--------------|------|------|------|
| **T1** | Stablecoin Architect | Polygon chain adapter | `backend/app/services/chain_adapter.py` + テスト | RPC URL 払出後にコード変更ゼロでスイッチ |
| **T2** | Stablecoin Architect | GCash sandbox adapter | `backend/app/services/gcash_adapter.py` + テスト | Coins.ph 接触後に env var 1 つで本物へ |
| **T3** | Engineer | iPhone scanner 強化 + 手動テスト チェックリスト | `frontend/scanner.js` 改修 + `docs/scanner-iphone-test-checklist.md` | iOS 16/17 graceful degradation |
| **T4** | Stablecoin Architect | LandBank ATM bridge mock + 仕様書 | `backend/app/services/landbank_bridge.py` + `docs/landbank-bridge-spec.md` + テスト | 4Ps 既存配給フローへの bolt-on |
| **T5** | Researcher | JICA 申請書 v1.1 (LoI テンプレ + DPG エビデンス) | `docs/handoff-packages/jica/04-letters-of-intent-templates.md` + `05-dpg-self-assessment-evidence.md` | プリスクリーン会話で即提示可 |
| **T6** | Researcher | Round 13 戦略会議英訳 | `docs/strategy-2026-05-round13-en.md` | i18n lag を 1 本維持 |

## 2. アダプタの設計原則

3 つのアダプタ (chain / gcash / landbank) すべて以下の構造:

```python
class XxxBackend(Protocol):
    """インターフェース。本物・mock 共通。"""
    def some_op(self, ...) -> ...: ...

class MockXxxBackend:
    """サンドボックスでも本物と同じ shape の応答を返す。"""

class RealXxxBackend:
    """本物の API/RPC を叩く。env var が揃った時のみ起動可。"""

def get_backend() -> XxxBackend:
    """env var で mock or real を選ぶ。デフォルト mock。"""
```

これにより:
- テストは常に Mock を使う (CI 緑が崩れない)
- 本番配備は env var を 1 行変えるだけ
- 段階的ロールアウト (一部 mock / 一部 real) も可能

## 3. JICA 申請書 v1 → v1.1 の改善点

JICA pre-screening を「すぐ通せる」状態にするための補強:

- **LoI (Letter of Intent) テンプレ**: JPYC / Coins.ph / Tokyo Innovation Base / Quezon City / DSWD の 5 通分。実際の役職者宛 + 1 ページ + 署名欄。
- **DPG Standard 9 指標 エビデンス appendix**: 各指標についてリポジトリ内ファイル/コミット参照を URL として明記。JICA 担当者が「動く証拠」をクリックで見られる。
- **予算 line item の根拠**: ¥65M 24 ヶ月の各項目について価格根拠 (例: AWS CloudHSM 月額 ¥62,500, Quantstamp audit 相場 ¥6M 等) を追記。

## 4. 検証目標

```
$ bash scripts/verify.sh all
[verify:pytest] 230+ passed (R14 214 → R15 +tbd)
✓ verify(all) all green

$ bash scripts/build_handoff_package.sh jica
→ /tmp/jpn-pbm-handoff-jica-2026-05-09.zip (LoI テンプレ + DPG エビデンス 含む)
```

## 5. ポイント精算 (ラウンド 14 = PR #15)

| エージェント | 内訳 | 合計 |
|--------------|------|------|
| **Engineer** | T1 multi-locale loader + T2 PH POS SDK + T5 handoff zip + verify mode | **+30** |
| **Researcher** | T3 R12 英訳 + T4 whitepaper §6.4 + T5 提出物 12 ファイル | **+30** |
| Stablecoin Architect | T2 GCash mock 設計レビュー | +15 |
| Cost Guardian | handoff package サイズ管理 | +10 |
| Red Team | DSWD Tagalog 文面のレビュー | +10 |
| Purpose Guardian | 監査トレイル整合性確認 | +10 |
| Legal | Data Privacy Act 文書整備 | +10 |
| その他 | 待機 +5 |

🥇 **MVP**: Engineer & Researcher 同点 (+30)。Round 11-14 で Engineer が連続 4 ラウンド MVP を取った後、Round 14 で Researcher が並んだ。

## 6. ラウンド 16 候補 (実外交解禁が必要な領域だけ残る)

サンドボックス内で出来ることはラウンド 15 で **本当に最終**。次は:

1. JICA pre-screening 会話 → v2 改訂
2. Polygon Mumbai testnet 実 RPC URL 取得 → `chain_adapter.py:RealChainBackend` 起動
3. Coins.ph 接触 → GCash sandbox API key 取得 → `gcash_adapter.py:RealGCashBackend` 起動
4. iPhone 13 / 15 実機での scanner verification
5. DSWD / Quezon City LGU との 4 者 MoU 合意
6. ホワイトペーパー v1.0 確定 (現状 v0.1 draft) と OECD/BIS/MAS 共有

## 7. Phase 完了率 (R14 → R15 想定)

| Phase | R14 | R15 (予定) |
|-------|-----|-----------|
| Phase 1 | 86% | 86% (変化なし、M+0 待ち) |
| Phase 2 | 71% | 71% (M+1 evidence 補強だが status は ready のまま) |
| Phase 3 | 40% | 40% (実外交ゼロのため変化なし) |

Round 15 の効果は「**進捗率の数字** ではなく **外部解禁時の即応性**」。これは数値で出ない、運用上の品質。
