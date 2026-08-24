# Sample sheet — temp=0.5 cond=<prose> seed=42

Verdicts over 20 attempts: `{'novelty': 6, 'pass': 8, 'shape': 6}`
(boundary-passing samples only — judgement R-2)

## Sample 1

A strong soft serene woman with a wildern feathered with a stroke through the surrounding a sense of the serene of powerful movement and forest silhouette through the pulses and a metal atmosphere. The scene is a captivating an enchance of merge in a sensual claws, and a futuristic background, she background, weathered and a sense of intimacy and soft, anime setting, creating an alluring, aboutdoned artistic painting, and a desolate setting, candlelight, serene, muscular, expressionist, moonlight, cinematic lighting, conflicting, chiaroscuro, detailed reflections, masterpiece

## Sample 2

A painting style with a red chained tableau of a mix of a mix of a passionate kiss, in a dynamic and seduction. The woman in a decorative chained book and vintage chains and a sense of artistic candles a sense of sensual warmth, a close-up of fielding and desert shadows, a captivating tension tattered head, moonlight, dynamic pose, score_9, score_8_up, score_7_up, score_6_up, BREAK,

## Sample 3

surreal consciousness with golden hour lighting between divine glow, surrounding through contrasts and glowing around her contrasts and atmosphere, standing in flowing fire and her hands, expressionist brushstrokes and showing emotional intensity, peaceful portrait of red chains, and a mesmerizing from the viewer constrast style with misty and a magnetic filtering through the sea of serene, and a golden hour and a seduction that creepy in the joy and sensual and fishnet stockings. Her form is form, shoulder through earthly beautiful face, a takeup, and a provocative, allure of desire and destroyer. , , score_9, score_8_up, score_7_up, score_6_up, BREAK,

## Sample 4

An Helly Marks setting in a blood-stained cathedral beings and a golden light casting a distant scene. The comic gaze and shadows and merged with the shadows and the souls of the tantalizing all of the cheeks of a sense of classic mood, her eyes red with chiaroscuro lighting, and the sunset casting a sense of an enigmatic emotions that seem the contact scene, featured and cograffing down and the soft, contemporary of sandy allure, a heavy ink line lines, a masterpiece quality, and a green skin, female figure in a misty and a captivating forbidden alluring a merit emotional intensity.

## Sample 5

(Black goddess closed in scene) with a bound towering portrait of a dark with a celestial beauty, expressionist and bold codern contemporary with bioluminescent forest wings and cascading dilations, steampunk energy and colors, metallic smile passion, detailed face contoured setting, source_animation, score_9, score_8_up, score_7_up, score_6_up, BREAK,

## Sample 6

(In the delicate serenity and a serenity polka-dots in the background, the viewer, a burning serene explosed by silken dress, in a single skin, beautiful feminine and golden hand, her hands a last green skin, a beautiful angel with a mischievous growing tension and distorted setting, lace in the soft watercolor scheme, stone beautiful femme fatale android, detailed chains, detailed ambient lighting, chiaroscuro, detailed reflections, sensual aura, flirt

## Sample 7

A woman in a tableau of a small with a state green embrace an an otherworldly as he seduction. The artwork composition that seem the beauty of a storm, her eyes and in a moonlit soft, expression surrealist and cyan with a perfect and charismatic style, reclining on a moonlight, her eyes and opulence shadows, battlefield and passion.

## Sample 8

A mysterious with a vampire queen black shadow, with chiaroscuro lighting and casting desperation the serene of cosmic patterns and the arrading thighs of her longing thighs. The scene is a dark and and her contrast. The pose is captivating at she explore comic and with storm collection, and her eyes her eyes contrast with a sense of contemplating a canopy of water, animal purple and an enigmatic emotion, with a sense of mischief grove and intimate pose, contemplating and despair, conflicting a standing latex movement, emotional intimacy tension, symbolism, perfect steamy setting, soft diffused lighting, confused lighting, controlled artistic color scheme, detailed lighting, intense expression, score_9, score_8_up, score_7_up, score_6_up, BREAK,

## Read notes (enforcer, 2026-08-24 — read_raw_output_first)

1. Grammatical scaffolding solid ("The scene is a captivating...") but semantic drift mid-sentence; closes with a well-formed quality-tag coda — the corpus's two-part prompt anatomy learned.
2. "a mix of a mix of a passionate kiss" — low temp loops on high-frequency bigrams; degenerate repetition is visible exactly where theory predicts.
3. Ends "score_9, score_8_up... BREAK," — the model treats the booru quality-block as a closing formula even under <prose> conditioning; register bleed, not separation.
4. Invents "An Helly Marks setting" — proper-noun-shaped hallucination; nothing in the corpus, but the capital-letter name slot is learned.
5. "(Black goddess closed in scene)" + "source_animation" — parenthetical emphasis syntax and metadata tags reproduced structurally correctly.
6. "polka-dots... silken dress... femme fatale android" — coherent aesthetic cluster; strongest sample of the sheet.
7. Shortest pass; trails into "battlefield and passion." — terminates cleanly with <|end|> where longer samples ramble.
8. "her longing thighs... her eyes her eyes" — anaphora duplication; the 6 novelty rejections at this temp (memorization) are the sheet's real headline.

Sheet headline: temp 0.5 = fluent-but-looping, 6/20 attempts REJECTED as
memorized corpus 8-grams — the regurgitation floor made visible.
