from __future__ import annotations

from .datamodels import (
    Comment,
    Indicator,
    NewsData,
    RiskFactorsData,
    RiskSummaryData,
    Threat,
)


class PulsediveParser:
    def extract_data_from_raw_data(self, raw_data):
        return raw_data.json()

    def build_indicator_object(self, raw_data, entity_type, comments):
        return Indicator(
            raw_data=raw_data,
            indicator_id=raw_data.get("iid", ""),
            indicator_name=raw_data.get("indicator", ""),
            indicator_type=raw_data.get("type", ""),
            risk_level=raw_data.get("risk", "unknown"),
            risk_recommended=raw_data.get("risk_recommended", "unknown"),
            manual_risk=raw_data.get("manual_risk", 0),
            retired_indicator=raw_data.get("retired", ""),
            indicator_added=raw_data.get("stamp_added", ""),
            indicator_updated=raw_data.get("stamp_updated", ""),
            indicator_seen=raw_data.get("stamp_seen", ""),
            indicator_probed=raw_data.get("stamp_probed", ""),
            indicator_retired=raw_data.get("stamp_retired", ""),
            recent=raw_data.get("recent", ""),
            risk_factors=self.build_risk_factor_results(raw_data=raw_data),
            comments=comments,
        )

    def build_risk_factor_results(self, raw_data):
        return [
            self.build_risk_factor_data(risk_factor_json)
            for risk_factor_json in raw_data.get("riskfactors", [])
        ]

    def build_risk_factor_data(self, raw_data):
        return RiskFactorsData(
            raw_data=raw_data,
            rfid=raw_data.get("rfid", ""),
            risk_description=raw_data.get("description", ""),
            risk=raw_data.get("risk", ""),
        )

    def build_comment_results(self, raw_data, limit):
        comment_list = []
        comment_limit = 0
        for comment_data_json in raw_data.get("comments", []):
            comment = self.build_comment_data(comment_data_json)
            comment_list.append(comment)
            comment_limit += 1
            if comment_limit == limit:
                break

        return comment_list

    def build_comment_data(self, raw_data):
        return Comment(
            raw_data=raw_data,
            comment_id=raw_data.get("cid", ""),
            unique_id=raw_data.get("uid", ""),
            user_comment=raw_data.get("username", ""),
            user_title=raw_data.get("title", ""),
            comment=raw_data.get("comment", ""),
            date_added=raw_data.get("stamp_added", ""),
            date_updated=raw_data.get("stamp_updated", ""),
        )

    def get_analysis_status(self, raw_data, comments=None):
        status = raw_data.get("status", "")

        return status

    def build_threat_object(self, raw_data, comments, news):
        return Threat(
            raw_data=raw_data,
            threat_id=raw_data.get("tid", ""),
            threat_name=raw_data.get("threat", ""),
            threat_category=raw_data.get("category", ""),
            threat_risk=raw_data.get("risk", "unknown"),
            threat_description=raw_data.get("description", ""),
            threat_wikisummary=raw_data.get("wikisummary", ""),
            threat_wikireference=raw_data.get("wikireference", ""),
            threat_retired=raw_data.get("retired", ""),
            threat_timestamp_added=raw_data.get("stamp_added", ""),
            threat_timestamp_updated=raw_data.get("stamp_updated", ""),
            threat_timestamp_seen=raw_data.get("stamp_seen", ""),
            threat_timestamp_retired=raw_data.get("stamp_retired", ""),
            threat_updated_last_domain=raw_data.get("updated_last_domain", ""),
            threat_comments=comments,
            threat_other_names=raw_data.get("othernames", ""),
            threat_risk_summary=self.build_risk_sumamry_results(
                raw_data.get("summary", {}).get("risk", {}),
            ),
            threat_news=news,
        )

    def build_risk_sumamry_results(self, raw_data):
        if type(raw_data) == dict:
            return RiskSummaryData(
                raw_data=raw_data,
                threat_unknown_indicators=raw_data.get("unknown", ""),
                threat_none_indicators=raw_data.get("none", ""),
                threat_low_indicators=raw_data.get("low", ""),
                threat_medium_indicators=raw_data.get("medium", ""),
                threat_high_indicators=raw_data.get("high", ""),
                threat_critical_indicators=raw_data.get("critical", ""),
                threat_total_indicators=raw_data.get("total", ""),
            )

    def build_news_results(self, raw_data, limit):
        news_list = []
        news_limit = 0
        for news_data_json in raw_data.get("news", []):
            news = self.build_news_data(news_data_json)
            news_list.append(news)
            news_limit += 1
            if news_limit == limit:
                break

        return news_list

    def build_news_data(self, raw_data):
        return NewsData(
            raw_data=raw_data,
            news_title=raw_data.get("title", ""),
            news_channel=raw_data.get("channel", ""),
            news_icon=raw_data.get("icon", ""),
            news_link=raw_data.get("link", ""),
            news_timestamp=raw_data.get("stamp", ""),
        )

    # Not Implemented
    def build_threat_links_object(self):
        raise NotImplementedError
