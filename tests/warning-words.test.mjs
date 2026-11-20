// The "Warning words found" card must show the words a review used, never a word-list pattern.
// Found on the live site on 16 Nov 2026: a list entry that is a regular expression was shown as the "word".
//   node --experimental-strip-types tests/warning-words.test.mjs
import { warningWords, matchedWords, isPattern } from '../src/lib/product.ts';

let failures = 0;
const check = (ok, what) => {
	console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`);
	if (!ok) failures += 1;
};
const sentence = (text, terms, tags = ['safety', 'defect']) => ({ text_raw: text, tags, terms });
const review = (...sentences) => ({ sentiment_analysis: { sentences } });
const ITCH = 'makati|nangati|nangangati|itch(?:y|ing)';
const NOT_WORKING = '(?:hindi|di|hnd|not)\\s+(?:po\\s+|sya\\s+)*(?:gumagana|gumana|working)';

const reviews = [
	review(sentence('Nangati ang balat ko', [{ ngram: ITCH, category: 'safety', span: [0, 7] }])),
	review(sentence('sobrang makati!', [{ ngram: ITCH, category: 'safety', span: [8, 15] }])),
	review(sentence('Makati talaga', [{ ngram: ITCH, category: 'safety', span: [0, 6] }])),
	review(sentence('hindi po gumagana', [{ ngram: NOT_WORKING, category: 'defect', span: [0, 17] }])),
	review(sentence('nagka allergy)', [{ ngram: 'allergic reaction|(?:nagka|nag)\\s?allerg\\w*', category: 'safety', span: [6, 14] }])),
	review(sentence('sira agad', [{ ngram: 'sira', category: 'defect', span: [0, 4] }])),
	review(sentence('no span here', [{ ngram: 'a|b', category: 'defect' }])),
	review(sentence('hindi makati', [{ ngram: ITCH, category: 'safety', span: [6, 12], negated: true }])),
];
const words = warningWords(reviews);
const shown = words.map((w) => w.word);

check(!shown.some((w) => isPattern(w)), `no pattern is shown as a word (${shown.join(' | ')})`);
check(shown.includes('nangati') && shown.includes('hindi po gumagana'), 'the words the reviews used are shown');
check(words.find((w) => w.word === 'makati')?.count === 2, 'the same word in two reviews is counted twice, whatever its capitals or punctuation');
check(shown.includes('allergy'), 'punctuation at the edges of the matched text is dropped');
check(shown.includes('sira'), 'a plain list word is shown as before');
check(!shown.includes('a|b') && !shown.includes(''), 'a pattern with no matched text is left out, not shown');
check(matchedWords(reviews[7]).size === 0, 'a negated match is still not a warning word');
check(isPattern(ITCH) && isPattern('nag\\s?allerg') && !isPattern('sira agad') && !isPattern("doesn't work"), 'patterns are told apart from plain words and phrases');
check(matchedWords(reviews[0]).has('nangati'), 'picking the shown word finds its review (same function gives both)');

const attributed = review(sentence('old overheated but replacement sparked', [
 { ngram: 'overheated', category: 'safety', span: [4, 14], excluded: 'attribution' },
 { ngram: 'sparked', category: 'safety', span: [31, 38] }
], ['safety']));
check(!matchedWords(attributed).has('overheated') && matchedWords(attributed).has('sparked'), 'excluded other-unit cues never reappear beside a retained current-unit flag');

console.log(failures ? `${failures} failed` : 'all passed');
process.exit(failures ? 1 : 0);
