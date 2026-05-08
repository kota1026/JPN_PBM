// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {PBM} from "../../contracts/PBM.sol";
import {PBMOfflineFallback} from "../../contracts/PBMOfflineFallback.sol";

/**
 * @title DeployPBM
 * @notice Polygon Mumbai testnet (chainId 80001) または Polygon mainnet (chainId 137)
 *         に PBM.sol + PBMOfflineFallback.sol をデプロイする Foundry script。
 *
 * 必須環境変数:
 *   GOVERNOR_PRIVKEY      : 32 byte hex (0x prefix なし)、faucet 受領済 testnet wallet
 *   JPYC_TESTNET_ADDRESS  : Mumbai 上の test JPYC ERC20 アドレス
 *
 * 使い方:
 *   forge script scripts/forge/DeployPBM.s.sol \
 *     --rpc-url $POLYGON_MUMBAI_RPC_URL \
 *     --broadcast --verify
 *
 * 期待されるガス見積 (Polygon Mumbai, 2026-05 時点):
 *   PBM.sol             ~2.1M gas (~¥0.04)
 *   PBMOfflineFallback  ~1.8M gas (~¥0.03)
 *   合計                ~¥0.07 / デプロイ
 */
contract DeployPBM is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("GOVERNOR_PRIVKEY");
        address jpyc = vm.envAddress("JPYC_TESTNET_ADDRESS");

        console.log("=== JPN-PBM Deployment ===");
        console.log("deployer:", vm.addr(deployerKey));
        console.log("jpyc    :", jpyc);
        console.log("chainId :", block.chainid);

        vm.startBroadcast(deployerKey);

        PBM pbm = new PBM(jpyc);
        console.log("PBM deployed at         :", address(pbm));

        PBMOfflineFallback fb = new PBMOfflineFallback(jpyc);
        console.log("PBMOfflineFallback at   :", address(fb));

        vm.stopBroadcast();

        console.log("=== Deployment complete ===");
        console.log("Next steps:");
        console.log("  1. JPYC.approve(PBM, BUDGET) from treasury");
        console.log("  2. PBM.createProgram(...) for first program");
        console.log("  3. PBMOfflineFallback.setApprovedStore(store, true) for each POS");
        console.log("  4. Verify: forge verify-contract --chain-id 80001 ...");
    }
}
