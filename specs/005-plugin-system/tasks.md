---
description: "Task list for plugin system + parameter miner"
---

# Tasks: PHANTOM Plugin System + Parameter Miner

**Input**: spec.md + approved mockup (docs/mockups/plugin-system-mockup.html)

- [x] T501 plugin_runs / plugin_results tables (migrations)
- [x] T502 Plugin framework: PhantomPlugin contract, registry, PluginEngine
      (background runs, WS plugin_progress/plugin_result/plugin_done, stop)
- [x] T503 `/api/plugins` routes (list/run/runs/results/stop/delete) + registration
- [x] T504 Parameter Miner plugin: wordlists (common-150, shallow-60), batched
      canary probing, reflection+behavior detection, bisection, double confirm,
      throttle + scope gate, hidden_param findings (dedupe-aware)
- [x] T505 Frontend: Plugins view (plugin/target/options pickers, live progress +
      results table with evidence + →Repeater), sidebar route, WS wiring
- [x] T506 Launch points: Proxy right-click → Plugins ▸ Parameter Miner,
      finding detail → Run Parameter Miner
- [x] T507 AI→Intruder bridge: payload extraction from the Copilot's last
      fenced answer, context request pre-fill, one-click send
- [x] T508 Tests: registry, planted-hidden-params local server (100% detection,
      0 FP, findings created), out-of-scope rejection (37 passing)
- [x] T509 Live verification through the real proxy + browser UI check
