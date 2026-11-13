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

export interface Conclusion {
	decision: ConclusionDecision;
	headline: string;
	text: string;
	/** The card's lead sentence, a paragraph that counts the reviews behind each concern, and the label beside it. */
	lead?: string;
	summary?: string;
	assessment?: string;
	assessment_note?: string;
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
