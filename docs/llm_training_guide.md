Understanding Syntax
To understand how an AI moves from processing raw data to actually "understanding" Zomi Tedim, we must look at how Large Language Models deconstruct and reconstruct human language.
Because base models like Llama-3 are trained primarily on English, teaching them a low-resource language requires them to learn entirely new grammatical rules. Here is the exact breakdown of how the model learns Zomi and what you must look for to verify its comprehension.
1. Tokenization (The Vocabulary Level)
Before the AI understands grammar, it must understand words. Llama-3 reads text in "tokens" (chunks of letters). Because Zomi was not in its original training, it will initially chop Zomi words into unnatural fragments.
* The Process: During training, the model maps the frequent token combinations from your Master Corpus to specific concepts.
* What to Look For: Watch for spelling stability. If the AI spells a word differently in the same paragraph or fuses words together improperly (e.g., writing inpen instead of in pen), it means the tokenization hasn't fully mapped to the Zolai standard.
2. Syntax and Word Order (The Structural Level)
English follows a Subject-Verb-Object (SVO) structure, such as "I (subject) eat (verb) rice (object)." Zomi generally follows a Subject-Object-Verb (SOV) structure.
* The Process: The AI must mathematically "unlearn" its default English word order and recognize that the verb typically anchors the end of a Zomi sentence.
* What to Look For: When you prompt the model, check the verb placement. If the AI generates a sentence that mirrors English word order using Zomi vocabulary, it is translating word-for-word rather than actually understanding the language's native syntax.
3. Morphological Markers (The Relational Level)
Zomi relies heavily on postpositional markers and particles to indicate the role of a word in a sentence, whereas English uses prepositions and word order.
* The Process: The model learns the statistical probability of particles like in (subject/agent marker), pen (topic marker), tawh (instrumental/associative marker), and te (plural marker) appearing after specific noun types.
* What to Look For: Evaluate the AI's use of relational particles. A model that truly understands Zomi will correctly attach in to the doer of the action and te strictly for pluralization. Misplacing these markers is the most common indicator that the model is guessing.
4. Semantic Context (The Meaning Level)
Words change meaning based on their context. The model uses its "attention mechanism" to look at all the words surrounding the current word to determine the correct output.
* The Process: By reading your 100,000+ line dataset, the AI learns which words frequently cluster together in specific scenarios (e.g., religious contexts from the Bible vs. news contexts from the web scraper).
* What to Look For: Test the model with words that have multiple meanings or test its grasp of idiomatic expressions. If it uses a formal Biblical term in a casual conversation context, its semantic mapping needs refinement.
When the current training run concludes, which of these four areas do you want to test first in your chat.py script?