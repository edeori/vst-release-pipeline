# Versioned installer rollout — 2026-10-19

User authorized the pending StringLife/DeathWings licensing fixes and WhirlDT DSP/UI fixes, builds, live publication, and Shop version updates. StringLife retains its production reviewer gate; the user approved the deployment. Other products use separate manual Publish workflows.

| Repository | Version | Build | Publish |
| --- | --- | --- | --- |
| StringLife-VST | 1.6.4 | [Run](https://github.com/edeori/StringLife-VST/actions/runs/39309402255) | [Run](https://github.com/edeori/StringLife-VST/actions/runs/39309402255) |
| DeathWings-VST | 0.1.16 | [Run](https://github.com/edeori/DeathWings-VST/actions/runs/39309413734) | [Run](https://github.com/edeori/DeathWings-VST/actions/runs/39310078355) |
| WhammyDT-VST | 0.4.6 | [Run](https://github.com/edeori/WhammyDT-VST/actions/runs/39309425298) | [Run](https://github.com/edeori/WhammyDT-VST/actions/runs/39310084254) |
| drum-sample-loader-VSTi | 0.1.1 | [Run](https://github.com/edeori/drum-sample-loader-VSTi/actions/runs/39309138516) | [Run](https://github.com/edeori/drum-sample-loader-VSTi/actions/runs/39310089327) |
| PAPI-550A-EQ-VST | 0.1.1 | [Run](https://github.com/edeori/PAPI-550A-EQ-VST/actions/runs/39309144040) | [Run](https://github.com/edeori/PAPI-550A-EQ-VST/actions/runs/39310095826) |
| Metamorphosis-VST | 0.1.59 | [Run](https://github.com/edeori/Metamorphosis-VST/actions/runs/39309149055) | [Run](https://github.com/edeori/Metamorphosis-VST/actions/runs/39310102095) |
| parametric-dynamic-eq-VST | 0.1.2 | [Run](https://github.com/edeori/parametric-dynamic-eq-VST/actions/runs/39305139718) | [Run](https://github.com/edeori/parametric-dynamic-eq-VST/actions/runs/39309411818) |

Both platforms use the metadata source SHA, including the bot version commit. Local checkouts were fast-forwarded to these commits while preserving unrelated edits. StringLife and DeathWings run the stable fingerprint smoke test on both runners. WhirlDT runs DSP and selector regression tests on both runners. Licensed builds remain explicitly enabled where licensing exists.

Swarm release registry had been disabled and its repository cleared in Shop; restored only these two fields. Shop version edits are scoped by product ID, with timestamped server backups.

Validation: live Mac PKG Distribution versions and downloaded live Windows EXE SHA-256 values are compared against the requested versions and clean Defender build reports. This does not constitute an end-to-end licensing-server activation test. Existing hostname-bound activations may require reactivation after the stable identifier migration; no local activation/trial records were deleted.

## Live verification

All seven build runs and publication runs completed successfully. The Shop version fields were updated only after the corresponding installers were published. Both HU and EN rendered product metadata were checked; ParaDyn EQ remains hidden as configured. Windows ProductVersion strings also match the release versions.

| Product | Version | Live Windows SHA-256 (matches clean Defender report) |
| --- | --- | --- |
| deathwings | 0.1.16 | `4a5fef39d62ba1411c321f34859639ba68958c9446bb1a54669480bd3f4c8208` |
| metamorphosis | 0.1.59 | `b79846cebbd9e24a28291d8e9b0202618651a1ee0f0123951009cbe196c42360` |
| papi550a-eq | 0.1.1 | `23e930cb82c81d9394b4ad0fe89e909e0e097026d7402a4694120788e0a4ec74` |
| paradyn-eq | 0.1.2 | `cb2d89848089ce6e17dd608d592e7571f563d60ed43eaa1d16aa93a3d42c812c` |
| stringlife | 1.6.4 | `88575aea702d629b788c68c06c1fbd2040328b07811f71a38a925cb1ce388911` |
| swarm | 0.1.1 | `2ffa2aaf3cfc1ca8e565e8ffc144486d7cc2ec616172368dd43d0195afef5807` |
| whirldt | 0.4.6 | `892faaa293fd4d643452ec733b2ee08317ad4c969a28350077dbf2048fe6220d` |
