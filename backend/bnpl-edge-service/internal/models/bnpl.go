package models

type CheckoutDeclineRequest struct {
	Amount               float64 `json:"amount"`
	DeclineReasonEncoded int     `json:"decline_reason_encoded"`
	TenureMonths         int     `json:"tenure_months"`
}

type FallbackOfferResponse struct {
	ShowBNPLOffer         bool    `json:"show_bnpl_offer"`
	ConversionProbability float64 `json:"conversion_probability"`
}
