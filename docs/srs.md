# Evidence-based design for a German vocabulary SRS bot

**Productive recall of simple word pairs beats most other formats for initial vocabulary learning — but the ideal system layers multiple card types as knowledge deepens.** Research from second language acquisition and cognitive psychology converges on a clear hierarchy: start with decontextualized word pairs for fast form-meaning mapping, then introduce cloze deletions and varied-context cards to build deeper, transferable knowledge. The most critical design choices involve always binding German nouns to their article from day one, prioritizing the L1→L2 (productive) direction, interleaving unrelated words rather than grouping semantics, and keeping each card atomic — one retrieval target per card. What follows is a synthesis of the evidence across all eight dimensions of your question, with concrete implementation recommendations for a Telegram-based system.

---

## Word pairs first, context sentences second

The strongest evidence on card format comes from Webb et al.'s 2020 meta-analysis (100 effect sizes, 22 studies): **flashcards and word lists produced ~77% meaning recall** on immediate tests, while fill-in-the-blank formats achieved only 43% and sentence writing just 18%. Laufer & Shmueli (1997) confirmed that words in isolation (lists) and minimal-context sentences were remembered better than words embedded in extended text, both short-term and long-term. Prince (1996) found less proficient learners benefit most from decontextualized translation pairs.

This does not mean context is worthless — far from it. Context sentences develop deeper word knowledge: collocations, grammatical behavior, usage patterns. Webb (2007) showed a single glossed sentence added little beyond a word pair for basic form-meaning mapping, but Schneider, Healy & Bourne (2002) demonstrated that varied-context practice creates "desirable difficulty" that enhances long-term retention and transfer. The practical synthesis is a layered approach:

- **Front of card**: English word/phrase (for productive cards) or German word with article (for receptive cards)
- **Back of card**: Target answer plus one short example sentence, an image (for concrete nouns), and audio pronunciation
- **Supplementary cloze cards**: Auto-generated from the example sentence once the word is partially learned, testing the word in context

Piotr Wozniak's minimum information principle remains the single most important card design rule: **each card should test exactly one atomic piece of knowledge**. Complex cards with multiple retrieval targets create partial-recall failures that confuse the scheduling algorithm. A card asking for "der Hund, die Hunde, Partizip II of bellen" is three cards pretending to be one.

---

## What to put on each side — and what the learner should recall

For **nouns**, the evidence is unequivocal: always learn the article as an inseparable unit with the noun. Every source — from university German programs to the Anki community — treats this as non-negotiable. Retrofitting gender later is extremely difficult. The card front shows the English word; the back shows "**der** Hund" with color coding (blue for masculine, red for feminine, green for neuter). Include the plural form ("die Hunde") on the back. When a noun follows a predictable suffix rule (e.g., -ung is always feminine), noting that pattern reinforces the gender system.

For **verbs**, the standard three-principal-parts format covers the forms that matter most: infinitive + 3rd person present (reveals stem changes) + Präteritum + Partizip II with auxiliary ("sprechen — spricht, sprach, hat gesprochen"). Irregular forms should be visually highlighted. Separable verbs need example sentences showing the separated form ("Ich stehe um 7 Uhr auf") because the infinitive alone ("aufstehen") doesn't teach real usage. Verb-preposition combinations (warten auf + Akk.) deserve their own dedicated cards showing the required case.

For **adjectives**, show the base form plus one declined example ("schnell → Das schnelle Auto"). For **phrases and idioms**, present the complete phrase as one unit with a literal translation if it illuminates the metaphor.

The question of recall vs. recognition has a clear answer from Webb (2009): **productive learning (L1→L2) produced larger gains across nearly all knowledge dimensions** — and critically, productive practice transferred well to receptive knowledge, while the reverse was not true. Webb's meta-analytic data showed productive learning yielded gains **22.4% higher** on form-recall tests. Griffin & Harley (1996) recommended the L1-to-L2 direction for the "most even accomplishment" across both production and recognition tests. The practical recommendation is to make the L1→L2 productive direction your primary card type, with L2→L1 recognition cards as a lighter supplementary format. Mental recall (not typing) is sufficient for most purposes, though typing helps specifically with orthography of difficult words.

---

## Why you should never teach kitchen words together

One of the most robust findings in vocabulary acquisition research directly contradicts common textbook practice: **semantic clustering — teaching words from the same category together — causes measurable interference**. Tinkham (1993) found learners needed nearly 50% more trials to learn semantically related word sets compared to unrelated sets, with cross-association errors at 25% vs. just 5%. Tinkham (1997), Waring (1997), and Erten & Tekin (2008) all replicated this finding across different language pairs and settings.

The mechanism is cross-association: when learning "der Löffel" (spoon), "die Gabel" (fork), and "das Messer" (knife) simultaneously, the learner's mind links all three meanings to all three forms, creating confusion. Nakata & Suzuki (2019) confirmed that semantically related items produce significantly more interference errors, even when overall posttest scores were similar.

However, Tinkham (1997) drew a crucial distinction: **thematic clustering facilitates learning** while semantic clustering hinders it. A thematic group like "restaurant: bestellen (verb), lecker (adjective), die Rechnung (noun), teuer (adjective)" works because items are different parts of speech connected by a shared schema, not coordinates under one category. The practical rules for your bot:

- **Never introduce semantically similar words in the same batch** (no "all colors" or "all furniture" sessions)
- **Interleave unrelated words** within each daily batch of new cards
- **Thematic grouping is acceptable** only if items span different word classes
- **Mix word types** (nouns, verbs, adjectives) within every review session

The cognitive psychology of interleaving reinforces this. Kornell & Bjork (2008) found interleaved study produced **59% accuracy vs. 36% for blocked study** on transfer tests. Rohrer & Taylor (2007) found interleaving tripled test scores in mathematics. One important note: learners consistently believe blocking works better even when interleaving produces objectively superior results — the metacognitive illusion is strong. Your bot should interleave by default without asking for preference.

---

## Sentences should be short, simple, and almost fully comprehensible

When example sentences appear on cards, research provides clear guidelines on their design. Hu & Nation (2000) established that learners need **95–98% vocabulary coverage** in a text for successful comprehension and inference of unknown words. Below 80% known vocabulary, context becomes too sparse to be useful. This maps directly to Krashen's i+1 principle: each sentence should contain exactly one unknown element (the target word), with everything else at the learner's current level.

Optimal sentence length is **8–15 words** — long enough to demonstrate usage but short enough to avoid cognitive overload. VanPatten (1990) showed that L2 learners are limited-capacity processors who attend to meaning before form; overloading the sentence with complexity steals processing resources from the target word. Barcroft (2004) demonstrated that sentence-level processing during initial learning can actually impair form encoding.

For German specifically, example sentences serve an especially important function: they demonstrate **case usage, word order, separable verb behavior, and adjective declension** — grammatical features that single-word cards cannot capture. A sentence like "Ich warte auf den Bus" teaches not just "warten" but the auf + accusative pattern. Sentences should scale with proficiency:

- **A1–A2**: Simple main clauses, present tense, familiar vocabulary ("Der Hund spielt im Garten")
- **B1**: Compound sentences, past tenses, subordinate clauses demonstrating V-final ("Ich habe den Film gesehen, weil mein Freund ihn empfohlen hat")
- **B2+**: Subjunctive, passive, complex embedding

Varying the sentence context across reviews creates Bjork's "desirable difficulty" — it prevents context-dependent learning where the word can only be recalled within one specific sentence frame. Your bot could store 2–3 example sentences per word and rotate them across reviews.

---

## Images, audio, and mnemonics are worth the engineering effort

Paivio's dual coding theory has strong empirical support: encoding information through both verbal and visual channels creates two independent retrieval pathways. The picture superiority effect is well-documented — people remember images substantially better than words alone. Gabriel Wyner, whose Fluent Forever method is one of the most sophisticated flashcard approaches, reports that adding images to his Russian grammar cards "made a huge difference." For concrete nouns, a relevant image (found via Google Images set to German) can replace the English translation entirely, encouraging direct L2-to-concept mapping rather than L2-to-L1-to-concept translation.

**Audio pronunciation is highly recommended** for German despite its relatively phonetic orthography. Key reasons: umlauts (ä, ö, ü) have no English equivalents, the ich-Laut/ach-Laut distinction (/ç/ vs. /x/) is unfamiliar, vowel length is phonemic (Bett vs. Beet), and stress patterns reveal separable vs. inseparable verbs (ÁUFstehen vs. verSTÉhen). Modern TTS quality is adequate for flashcards and dramatically easier to generate at scale than sourcing native recordings. Include both word-level and sentence-level audio when possible.

For gender mnemonics, Wyner's approach assigns vivid actions to each gender — masculine nouns explode, feminine nouns catch fire, neuter nouns shatter like glass. The keyword mnemonic method has strong research backing for German specifically: Fritz et al. (2007) found it superior to rote rehearsal, and Springer (2019) showed that combining keyword mnemonics with retrieval practice produced the strongest results at 48-hour and 1-week delays. However, mnemonics work best selectively for difficult items rather than as a universal strategy for all vocabulary.

---

## Different word categories deserve tailored — but unified — templates

The MonoglotAnxiety German Anki template offers the best practical model: a single unified note type with conditional fields, rather than separate templates per word class. Early over-engineering (8+ fields, separate templates for nouns/verbs/adjectives) makes card creation unsustainable. Instead, use one "info" field that adapts based on word type:

- **Nouns**: info field contains plural form ("die Hunde"), optionally genitive ("des Hundes")
- **Verbs**: info field contains "spricht, sprach, hat gesprochen" with irregular forms highlighted
- **Adjectives**: info field contains comparative/superlative if irregular ("gut, besser, am besten")
- **Phrases**: info field contains literal translation or usage note

From each note, auto-generate up to three card types: a productive card (English → German), a receptive card (German → English), and a cloze deletion card from the example sentence. Use a `recognition_only` flag for words that only need passive knowledge (technical terms, formal vocabulary).

**Word families** are worth teaching but should be introduced gradually, not simultaneously. When a learner knows "fahren," later cards for "der Fahrer," "die Fahrt," "erfahren," and "die Abfahrt" can reference the root — this leverages morphological awareness, which Görgen (2021) showed explains the highest unique variance in reading and spelling for German. Teach common prefixes (ver-, be-, er-, ent-) and suffixes (-ung, -keit, -lich) as their own cards to unlock productive morphological guessing.

---

## Batching, pacing, and handling failure

The evidence on new card introduction is consistent: **5–10 new cards per day** is the sustainable range for most learners. The rule of thumb is to multiply daily new cards by 7 to estimate the steady-state daily review load in two weeks. At 10 new cards per day, expect roughly 70 reviews daily — about 15–20 minutes. Cowan's (2001) working memory research suggests a hard limit of approximately **4 ± 1 truly novel chunks** that can be held in working memory simultaneously, which argues for brief initial learning sessions followed by spaced review.

The first review should occur within **24 hours** of introduction — this aligns with Cepeda et al.'s (2008) finding that the optimal spacing gap is approximately 10–20% of the desired retention interval. Modern adaptive algorithms like FSRS, which model individual forgetting curves per item, are superior to fixed-ratio approaches and should be used if available.

For leeches (cards failed repeatedly), the community consensus is clear: suspend at 4–6 lapses (lower than Anki's default of 8), then reformulate the card. Common fixes include adding an image, improving the example sentence, creating a mnemonic, or splitting a complex card into simpler sub-cards. Many leeches are caused by interference between similar words — detecting and addressing these confusable pairs proactively is what Wozniak calls "probably the single greatest cause of forgetting."

---

## Conclusion: a phased architecture that grows with the learner

The optimal system is not one card format but a progression. **Phase 1** (first 500–1000 words): productive word-pair cards (English → German with article), color-coded gender, one example sentence on the back, an image for concrete nouns, and audio. **Phase 2** (1000–3000 words): add auto-generated cloze deletions from example sentences, introduce varied contexts across reviews, and begin monolingual definitions for high-frequency words. **Phase 3** (3000+ words): sentence-mined cards from authentic content, with the German sentence on front and a single unknown word to decode.

Three design principles should guide every implementation decision. First, **one retrieval target per card** — the minimum information principle is the single highest-leverage rule. Second, **productive recall over passive recognition** — the 22% advantage in Webb's meta-analysis compounds over thousands of cards. Third, **interleave aggressively** — the brain learns categories by contrast, not by repetition within a cluster. The research is remarkably convergent: a well-designed simple system, used consistently for 15–20 minutes daily, will outperform any elaborate system used sporadically. Build for sustainability first, sophistication second.