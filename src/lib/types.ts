// The shapes the Flask app sends. The server words every verdict and label
// (dashboard_utils.badge_view), so this app only lays them out.

export type Tone = 'high' | 'moderate' | 'low' | 'unknown';

export type VerdictState =
	| 'safety_warning'
	| 'possible_safety_issue'
	| 'possible_counterfeit_or_defect'
	| 'reviews_may_be_unreliable'
	| 'no_warning_signs'
	| 'insufficient_evidence'
	| 'not_analyzed';

export type Category = 'safety' | 'defect' | 'quality' | 'counterfeit' | 'not_as_described';

export interface Evidence {
	text: string;
	rating: number | null;
	hazard: string | null;
	/** [start, end] character ranges of the words that triggered the quote. */
	highlights: [number, number][];
}

export interface Badge {
	category: Category;
	label: string;
	helper: string;
	informs_only: boolean;
	mentions: number;
	reviews_analyzed: number;
	phrase: string;
	summary: string;
	evidence: Evidence[];
	more_evidence: number;
}

export interface LabelInfo {
	category: Category;
	label: string;
	helper: string;
	informs_only: boolean;
}

export interface SafetyCheckAccuracy {
	sentences_checked: number;
	reports_confirmed: number;
	reports_caught: number;
	flags_raised: number;
	flags_confirmed: number;
}

/** What the reviews add up to, in words ("Based on the reviews of this product ..."). Worked out by the server. */
export type ConclusionDecision = 'recommended' | 'mixed' | 'caution' | 'not_recommended' | 'not_enough';

/** One quotation behind a claim: the reviewer's own words, where they sit in the review, and which review it is. */
export interface AspectQuote {
	review_id: string;
	text: string;
	/** [start, end) in the original review text, or null when the position could not be found. */
	span: [number, number] | null;
	language: 'en' | 'fil' | 'taglish';
	rating: number | null;
	evidence: string;
}

/** One line of "Why this conclusion?": a count of distinct reviews that can be reproduced from the review text. */
export interface WhyItem {
	aspect: string;
	kind: 'product' | 'trust' | 'service';
	polarity: 'positive' | 'negative';
	reviews: number;
	text: string;
	quotes: AspectQuote[];
	review_ids: string[];
	ids_truncated: boolean;
}

export interface ConclusionEvidence {
	status: 'supported' | 'limited';
	reviews_considered: number;
	product_reviews: number;
	service_reviews: number;
	not_used_yet_reviews: number;
	skipped_clauses: Record<string, number>;
	rules_version: string;
	category: string | null;
	why: WhyItem[];
}

export interface Conclusion {
	decision: ConclusionDecision;
	headline: string;
	text: string;
	/** The card's lead sentence, a paragraph that counts the reviews behind each concern, and the label beside it. */
	lead?: string;
	summary?: string;
	assessment?: string;
	assessment_note?: string;
	/** The paragraph without the hazard sentences, and those sentences on their own (safety and authenticity reports). `summary` has all of it. */
	body?: string;
	warnings?: string[];
	/** 'limited' when the reviews say little about the product itself (delivery and packaging only, or too few opinions). */
	evidence_status?: 'supported' | 'limited';
	/** Only on the product page, and only when the saved report kept its review text. */
	evidence?: ConclusionEvidence;
	points: string[];
	basis: { reviews: number; positive?: number; uncertain?: number; negative?: number };
	notice: string;
}

export interface BadgeView {
	available: boolean;
	state: VerdictState;
	tone: Tone;
	headline: string;
	detail: string;
	reviews_analyzed: number;
	counts: Partial<Record<Category, number>>;
	badges: Badge[];
	labels: LabelInfo[];
	limits_notice?: string | null;
	safety_check_accuracy?: SafetyCheckAccuracy;
	/** Null when the product was not analyzed, or when there is nothing to base a conclusion on. */
	conclusion?: Conclusion | null;
}

export interface Term {
	span?: [number, number];
	ngram?: string;
	category?: string;
	negated?: boolean;
}

export interface Sentence {
	text_raw?: string;
	tags?: string[];
	extra_tags?: string[];
	terms?: Term[];
	extra_terms?: Term[];
}

export interface Review {
	author?: string;
	rating?: number;
	time?: string;
	date?: string;
	content?: string;
	is_duplicate?: boolean;
	included_in_analysis?: boolean;
	sentiment_analysis?: {
		label?: string;
		review_tags?: string[];
		review_extra_tags?: string[];
		sentences?: Sentence[];
		sentiment?: {
			category_context?: {
				revision: string;
				status: 'agrees' | 'differs' | 'ambiguous' | 'no_signal' | 'unclassified' | 'unavailable' | 'expected_behavior';
				initial_label: string;
				context_signal: 'positive' | 'negative' | null;
				used_for_decision: false;
				sentiment_overridden: false;
			};
		};
	};
}

export interface SentimentSummary {
	sentiment_counts?: { positive?: number; uncertain?: number; neutral?: number; negative?: number };
	sentiment_shares?: Record<string, number>;
	duplicate_review_count?: number;
	coverage?: {
		reviews_listed?: number;
		reviews_available?: number;
		sampling?: string;
		star_quota?: number;
		weighted?: boolean;
	};
}

export interface Product {
	name?: string;
	link: string;
	price?: string;
	rating?: number;
	category?: string;
	/** Rule-derived from the listing title; `other` means no recognized category. */
	product_category?: string;
	product_group?: string;
	platform?: string;
	img?: string;
	image?: string;
	image_url?: string;
	thumbnail?: string;
	analysis_date?: string;
	analyzed_at?: string;
	updated_at?: string;
	/** False when the saved report was made by an earlier version of the checker (server.py adds it). */
	checked_with_current?: boolean;
	reviews_collected?: number;
	comments?: Review[];
	sentiment_summary?: SentimentSummary;
	badge_view?: BadgeView;
}

export interface ActivityEntry {
	product: Product;
	openedAt: number;
}

export interface Library {
	activity: Record<string, ActivityEntry>;
	wishlist: string[];
	clearedAt: number;
}

export interface GuestStatus {
	limit: number;
	left: number;
}

export interface Me {
	user: { name: string; email: string; created_at?: string } | null;
	guest: GuestStatus | null;
}

export interface Job {
	id: string;
	state: 'running' | 'complete' | 'error';
	stage: number;
	stage_label: string;
	progress: number;
	message: string;
	/** A Chrome window has opened for a login or a check, and `message` says what to do in it. */
	needs_you?: boolean;
	/** On the public site: the window is on the team's scanning computer, so a team member has to act, not the visitor. */
	needs_team?: boolean;
	platform: string;
	query: string;
	created_at: string;
	product_count?: number;
}

export type Marketplace = 'shopee' | 'lazada' | 'temu';
