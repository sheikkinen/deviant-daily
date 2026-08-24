# Ramp Install Manifest

Written by scripts/ramp.sh (FR-865). Sufficient for rollback:
`scripts/ramp.sh <this-repo> --rollback` deletes only `created`
rows (hash-verified) and restores `overwritten` rows from backup.

- source_sha: 560a27145f3d7cb504f5248de5217de03d21107e
- reviewed_source_sha: pending-human-review
- tier: 3

| destination | source | action | source_sha256 | installed_sha256 | backup |
|---|---|---|---|---|---|
| .pre-commit-config.yaml | assets/tier1/pre-commit-config.yaml | created | 01283132b233acf6e213935b1f4802f2572d2426b977a4cdceb6b76f16d12926 | 01283132b233acf6e213935b1f4802f2572d2426b977a4cdceb6b76f16d12926 | - |
| .github/hooks/pre-command-guard.json | assets/tier1/github/hooks/pre-command-guard.json | created | 99caa72de1b9f00a34c919f3962bd4069711971bc600c60343e275620b90ebf5 | 99caa72de1b9f00a34c919f3962bd4069711971bc600c60343e275620b90ebf5 | - |
| .github/hooks/scripts/pre-command-guard.sh | assets/tier1/github/hooks/scripts/pre-command-guard.sh | created | 1657f925218a192e1115bc8eb2b0415bc859368c54e58b0afcbdb36bc68122a2 | 1657f925218a192e1115bc8eb2b0415bc859368c54e58b0afcbdb36bc68122a2 | - |
| .github/hooks/README.md | assets/tier1/github/hooks/README.md | created | 135f37d4f1d5f12c6f1e23fb1a8a335203762649e4d7bc1e19cb67c66c0dbbfb | 135f37d4f1d5f12c6f1e23fb1a8a335203762649e4d7bc1e19cb67c66c0dbbfb | - |
| .github/workflows/tests.yml | assets/tier1/github/workflows/tests.yml | created | c8526aff597c6f1d0f97f0b3d2285b8e9a4791e69143a6c559898db9cd767276 | c8526aff597c6f1d0f97f0b3d2285b8e9a4791e69143a6c559898db9cd767276 | - |
| AGENTS.md | assets/tier1/AGENTS.md | created | f4edf7512f2c20565c66aa7c7cd2b59cf34df9123778eb75108d526d230a2f4a | f4edf7512f2c20565c66aa7c7cd2b59cf34df9123778eb75108d526d230a2f4a | - |
| feature-requests/TEMPLATE.md | assets/tier2/feature-requests/TEMPLATE.md | created | cb107660252ed1b4aa121c63882e66783534424da7de585f6b539daa01d50645 | cb107660252ed1b4aa121c63882e66783534424da7de585f6b539daa01d50645 | - |
| .github/skills/judge-fr/SKILL.md | assets/tier2/github/skills/judge-fr/SKILL.md | created | bbea003b040d9b2bfe882d3543802628d16278c77c4e034f98bf6d88f31fb747 | bbea003b040d9b2bfe882d3543802628d16278c77c4e034f98bf6d88f31fb747 | - |
| .github/skills/judge-fr/doctrine.md | assets/tier2/github/skills/judge-fr/doctrine.md | created | 19c54ac5c7c278ea98a8e4b0dc00e06f0086a89dd0a5a14a48caee59cee81740 | 19c54ac5c7c278ea98a8e4b0dc00e06f0086a89dd0a5a14a48caee59cee81740 | - |
| .github/skills/judge-fr/judgement.template.md | assets/tier2/github/skills/judge-fr/judgement.template.md | created | ee50eac9b88df18c1681c178209d506e784664e1df0e62840178e70c54106ba8 | ee50eac9b88df18c1681c178209d506e784664e1df0e62840178e70c54106ba8 | - |
| .github/skills/review-pr/SKILL.md | assets/tier2/github/skills/review-pr/SKILL.md | created | 707fd275de678691b82ce848987ef79fde7c013596719aa01f09df90e5a1fc97 | 707fd275de678691b82ce848987ef79fde7c013596719aa01f09df90e5a1fc97 | - |
| .github/skills/review-pr/doctrine.md | assets/tier2/github/skills/review-pr/doctrine.md | created | 14c4e8f96cbc78d08a679dfb3c1fbf24fd2ba314ca53b6b1ec22511678287e9c | 14c4e8f96cbc78d08a679dfb3c1fbf24fd2ba314ca53b6b1ec22511678287e9c | - |
| .github/skills/review-pr/review.template.md | assets/tier2/github/skills/review-pr/review.template.md | created | 5671c6aa390a9adaa55c0557c2c7534848d0aedb36f07a4f70686fd69228837a | 5671c6aa390a9adaa55c0557c2c7534848d0aedb36f07a4f70686fd69228837a | - |
| scripts/judge.sh | assets/tier2/scripts/judge.sh | created | ac3a01d3849cbea09fb10f22d1dcf2082b1c86a0c3a657c1df1a95033df6458b | ac3a01d3849cbea09fb10f22d1dcf2082b1c86a0c3a657c1df1a95033df6458b | - |
| scripts/review.sh | assets/tier2/scripts/review.sh | created | 99dafc9d350aaf8c83c892b156ae195c4b4fbc7ab9209f3c87dc4348503962b6 | 99dafc9d350aaf8c83c892b156ae195c4b4fbc7ab9209f3c87dc4348503962b6 | - |
| scripts/gates/changelog_gate.sh | assets/tier2/scripts/gates/changelog_gate.sh | created | 68a3ac924d7c920735a19bbf7ed487edcc5fe2b851422b061d875aa29c2495a1 | 68a3ac924d7c920735a19bbf7ed487edcc5fe2b851422b061d875aa29c2495a1 | - |
| scripts/gates/diary_gate.sh | assets/tier2/scripts/gates/diary_gate.sh | created | c9347e784923ce62c96a904367c9bf584db81bdcf066646e680dabf1c848b498 | c9347e784923ce62c96a904367c9bf584db81bdcf066646e680dabf1c848b498 | - |
| docs/diary/TEMPLATE.md | assets/tier2/docs/diary/TEMPLATE.md | created | 5a43a6d235f2163410fb8702ea2049924926f5c77cdeb5927aa888a76b5a9466 | 5a43a6d235f2163410fb8702ea2049924926f5c77cdeb5927aa888a76b5a9466 | - |
| capabilities/README.md | assets/tier3/capabilities/README.md | created | afe6821b9a2e8f9c7f7cfa690145bbc59a39493318e4276d4328bbca9cb32ea0 | afe6821b9a2e8f9c7f7cfa690145bbc59a39493318e4276d4328bbca9cb32ea0 | - |
| scripts/req_coverage.py | assets/tier3/scripts/req_coverage.py | created | 8a4b9da91b7bfaca355abafe9ab20895a832f9e06a594a7c560ec6ce6a837ae2 | 8a4b9da91b7bfaca355abafe9ab20895a832f9e06a594a7c560ec6ce6a837ae2 | - |
