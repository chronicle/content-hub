from __future__ import annotations

from TIPCommon import add_prefix_to_dict

from .constants import (
    CRITICAL_RISK_FACTOR_IMAGE,
    DATA_ENRICHMENT_PREFIX,
    HIGH_RISK_FACTOR_IMAGE,
    LOW_RISK_FACTOR_IMAGE,
    MEDIUM_RISK_FACTOR_IMAGE,
    RISK_NAME,
    RISK_SCORE,
    UNKNOWN_RISK_FACTOR_IMAGE,
    VERY_LOW_RISK_FACTOR_IMAGE,
)


class BaseModel:
    """Base model for inheritance"""

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class PulsediveEntity(BaseModel):
    def __init__(
        self,
        raw_data,
        indicator_updated,
        risk_level,
        risk_recommended,
        indicator_retired,
    ):
        super(PulsediveEntity, self).__init__(raw_data)
        self.indicator_updated = indicator_updated
        self.risk_level = risk_level
        self.risk_recommended = risk_recommended
        self.indicator_retired = indicator_retired

    def get_enrichment_data(self):
        raise NotImplementedError

    def to_enrichment_data(self):
        clean_enrichment_data = {
            k: v for k, v in self.get_enrichment_data().items() if v
        }
        return add_prefix_to_dict(clean_enrichment_data, DATA_ENRICHMENT_PREFIX)

    def to_json(self, comments=None):
        if comments:
            self.raw_data["comments"] = [comment.to_json() for comment in comments]

        return self.raw_data

    @property
    def threshold(self):
        return self.risk_level


class PulsediveThreats(BaseModel):
    def __init__(self, raw_data):
        super(PulsediveThreats, self).__init__(raw_data)

    def get_enrichment_data(self):
        raise NotImplementedError

    def to_enrichment_data(self):
        raise NotImplementedError
        # clean_enrichment_data = {k: v for k, v in self.get_enrichment_data().items() if v}
        # return add_prefix_to_dict(clean_enrichment_data, DATA_ENRICHMENT_PREFIX)

    def to_json(self, comments=None, news=None):
        if comments:
            self.raw_data["comments"] = [comment.to_json() for comment in comments]

        if news:
            self.raw_data["news"] = [threat_news.to_json() for threat_news in news]

        return self.raw_data

    @property
    def threshold(self):
        return self.risk_level


class RedirectsData(BaseModel):
    def __init__(self, raw_data, iid=None, indicator=None):
        super(RedirectsData, self).__init__(raw_data)
        self.iid = iid
        self.indicator = indicator


class RiskFactorsData(BaseModel):
    def __init__(self, raw_data, rfid=None, risk_description=None, risk=None):
        super(RiskFactorsData, self).__init__(raw_data)
        self.rfid = rfid
        self.risk_description = risk_description
        self.risk = risk


class Indicator(PulsediveEntity):
    def __init__(
        self,
        raw_data,
        indicator_id,
        indicator_name,
        indicator_type,
        risk_level,
        risk_recommended,
        manual_risk,
        retired_indicator,
        indicator_added,
        indicator_updated,
        indicator_seen,
        indicator_probed,
        indicator_retired,
        recent,
        risk_factors,
        comments,
    ):
        super(Indicator, self).__init__(
            raw_data,
            indicator_updated,
            risk_level,
            risk_recommended,
            indicator_retired,
        )
        self.indicator_id = indicator_id
        self.indicator_name = indicator_name
        self.indicator_type = indicator_type
        self.risk_level = risk_level
        self.risk_recommended = risk_recommended
        self.manual_risk = manual_risk
        self.retired_indicator = retired_indicator
        self.indicator_added = indicator_added
        self.indicator_updated = indicator_updated
        self.indicator_seen = indicator_seen
        self.indicator_probed = indicator_probed
        self.indicator_retired = indicator_retired
        self.risk_factors = risk_factors
        self.comments = comments

    def get_enrichment_data(self):
        enrichment_data = {
            "id": self.indicator_id,
            "indicator_type": self.indicator_type,
            "risk_level": self.risk_level,
            "risk_recommended": self.risk_recommended,
            "manual_risk": self.manual_risk,
            "retired_indicator": self.retired_indicator,
            "indicator_added": self.indicator_added,
            "indicator_updated": self.indicator_updated,
            "indicator_seen": self.indicator_seen,
            "indicator_probed": self.indicator_probed,
            "indicator_retired": self.indicator_retired,
        }

        return enrichment_data

    def to_insight(self, threshold):
        risky = 0
        if int(RISK_SCORE.get(self.risk_level)) >= int(
            RISK_SCORE.get(RISK_NAME.get(threshold)),
        ):
            risky = 1

        content = ""
        content += "<table style='100%'><tbody>"
        content += (
            "<tr><td style='text-align: left; width: 30%;'><strong style='font-size: 15px'>"
            "Detected:  <span {threshold_style}>{threshold}</span></strong></td>".format(
                threshold_style=" style='color: #ff0000'" if risky else "",
                threshold=self.threshold,
            )
        )
        content += (
            "<td style='text-align: left; width: 30%;'><strong style='font-size: 15px'> Risk: "
            f"{threshold}</strong></td></tr>"
        )
        content += "</tbody></table><br>"
        content += "<table style='100%'><tbody>"
        content += (
            "<tr><td style='text-align: left; width: 30%;'><strong>Indicator: </strong></td>"
            f"<td style='text-align: left; width: 30%'>{self.indicator_name}</td></tr>"
        )
        content += (
            "<tr><td style='text-align: left; width: 30%;'><strong>Risk: </strong></td>"
            f"<td style='text-align: left; width: 30%;'>{self.risk_level}</td></tr>"
        )
        content += (
            "<tr><td style='text-align: left; width: 30%;'><strong>Recommended Risk: </strong></td>"
            f"<td style='text-align: left; width: 30%;'>{self.risk_recommended}</td></tr>"
        )
        content += "</tbody></table><br><br>"
        if self.risk_factors:
            content += "<p><strong>Risk Factors: </strong></p>"
            content += "<table><tbody>"
            for risk_factor in self.risk_factors:
                if risk_factor.risk == "none":
                    risk_image = VERY_LOW_RISK_FACTOR_IMAGE
                elif risk_factor.risk == "low":
                    risk_image = LOW_RISK_FACTOR_IMAGE
                elif risk_factor.risk == "medium":
                    risk_image = MEDIUM_RISK_FACTOR_IMAGE
                elif risk_factor.risk == "high":
                    risk_image = HIGH_RISK_FACTOR_IMAGE
                elif risk_factor.risk == "critical":
                    risk_image = CRITICAL_RISK_FACTOR_IMAGE
                else:
                    risk_image = UNKNOWN_RISK_FACTOR_IMAGE
                content += f"<tr><td width='10%'><img {risk_image} height='20px' width='12px' /></td>"
                content += f"<td>{risk_factor.risk_description}</td></tr>"
        content += "</tbody></table><br>"

        return content


class Threat(PulsediveThreats):
    def __init__(
        self,
        raw_data,
        threat_id,
        threat_name,
        threat_category,
        threat_risk,
        threat_description,
        threat_wikisummary,
        threat_wikireference,
        threat_retired,
        threat_timestamp_added,
        threat_timestamp_updated,
        threat_timestamp_seen,
        threat_timestamp_retired,
        threat_updated_last_domain,
        threat_comments,
        threat_other_names,
        threat_risk_summary,
        threat_news,
    ):
        super(Threat, self).__init__(raw_data)
        self.threat_id = threat_id
        self.threat_name = threat_name
        self.threat_category = threat_category
        self.threat_risk = threat_risk
        self.threat_description = threat_description
        self.threat_wikisummary = threat_wikisummary
        self.threat_wikireference = threat_wikireference
        self.threat_retired = threat_retired
        self.threat_timestamp_added = threat_timestamp_added
        self.threat_timestamp_updated = threat_timestamp_updated
        self.threat_timestamp_seen = threat_timestamp_seen
        self.threat_timestamp_retired = threat_timestamp_retired
        self.threat_updated_last_domain = threat_updated_last_domain
        self.threat_comments = threat_comments
        self.threat_other_names = threat_other_names
        self.threat_risk_summary = threat_risk_summary
        self.threat_news = threat_news

    def get_enrichment_data(self):
        enrichment_data = {
            "id": self.threat_id,
            "threat_name": self.threat_name,
            "threat_category": self.threat_category,
            "threat_risk": self.threat_risk,
            "threat_description": self.threat_description,
            "threat_wikisummary": self.threat_wikisummary,
            "threat_wikireference": self.threat_wikireference,
            "threat_retired": self.threat_retired,
            "threat_timestamp_added": self.threat_timestamp_added,
            "threat_timestamp_updated": self.threat_timestamp_updated,
            "threat_timestamp_seen": self.threat_timestamp_seen,
            "threat_timestamp_retired": self.threat_timestamp_retired,
            "threat_updated_last_domain": self.threat_updated_last_domain,
            "threat_other_names": self.threat_other_names,
            "threat_risk_summary": self.threat_risk_summary,
        }

        return enrichment_data

    def to_insight(self):
        content = ""
        content += "<table style='100%'><tbody>"
        content += (
            "<tr><td style='text-align: left; width: 30%;'><strong style='font-size: 15px'>"
            f"Threat Name:  <span>{self.threat_name}</span></strong></td>"
        )
        content += (
            "<td style='text-align: left; width: 30%;'><strong style='font-size: 15px'> Risk: "
            f"{self.threat_risk}</strong></td></tr>"
        )
        content += "</tbody></table><br>"
        content += "<table style='100%'><tbody>"
        content += (
            "<tr><td style='text-align: left; width: 30%; font-size: 15px'><strong>Category: </strong></td>"
            f"<td style='text-align: left; width: 30%; font-size: 15px'>{self.threat_category}</td></tr>"
        )
        content += "</tbody></table><br>"
        if self.threat_risk_summary:
            content += "<p style='font-size: 15px'><strong>Risk Summary: </strong></p>"
            content += "<table><tbody>"
            content += (
                "<tr><td style='text-align: left; width: 30%;'>Unknown: </td>"
                f"<td style='text-align: center; width: 30%;'>{self.threat_risk_summary.threat_unknown_indicators}</td></tr>"
            )
            content += (
                "<tr><td style='text-align: left; width: 30%;'>Very Low: </td>"
                f"<td style='text-align: center; width: 30%;'>{self.threat_risk_summary.threat_none_indicators}</td></tr>"
            )
            content += (
                "<tr><td style='text-align: left; width: 30%;'>Low: </td>"
                f"<td style='text-align: center; width: 30%;'>{self.threat_risk_summary.threat_low_indicators}</td></tr>"
            )
            content += (
                "<tr><td style='text-align: left; width: 30%;'>Medium: </td>"
                f"<td style='text-align: center; width: 30%;'>{self.threat_risk_summary.threat_medium_indicators}</td></tr>"
            )
            content += (
                "<tr><td style='text-align: left; width: 30%;'>High: </td>"
                f"<td style='text-align: center; width: 30%;'>{self.threat_risk_summary.threat_high_indicators}</td></tr>"
            )
            content += (
                "<tr><td style='text-align: left; width: 30%;'>Critical: </td>"
                f"<td style='text-align: center; width: 30%;'>{self.threat_risk_summary.threat_critical_indicators}</td></tr>"
            )
            content += "<tr><td style='text-align: left; width: 30%;'><hr></td><td style='text-align: left; width: 30%;'><hr></td></tr>"
            content += (
                "<tr><td style='text-align: left; width: 30%; font-size: 15px;'><strong>Total: </strong></td>"
                f"<td style='text-align: center; width: 30%; font-size: 15px;'><strong>{self.threat_risk_summary.threat_total_indicators}</strong></td></tr>"
            )
            content += "</tbody></table><br>"
        if self.threat_wikisummary:
            content += "<p style='font-size: 15px'><strong>Wiki Summary: </strong></p>"
            content += "<table><tbody>"
            content += f"<tr><td style='text-align: left; width: 30%;'>{self.threat_wikisummary}</td></tr><br>"
            content += "</tbody></table><br>"
        if self.threat_news:
            content += "<p style='font-size: 15px'><strong>News: </strong></p>"
            content += "<table style='100%'><tbody>"
            content += "<tr><td style='text-align: left; width: 30%;'><strong>Title</strong></td>"
            content += (
                "<td style='text-align: left; width: 30%;'><strong>Link</strong></td>"
            )
            content += "<td style='text-align: left; width: 30%;'><strong>Published</strong></td></tr>"
            for news_items in self.threat_news:
                content += f"<tr><td style='text-align: left; width: 30%; padding-right: 5px;'>{news_items.news_title}</td>"
                content += f"<td style='text-align: left; width: 30%;'><a href={news_items.news_link}>{news_items.news_channel}</a></td>"
                content += f"<td style='text-align: left; width: 30%;'>{news_items.news_timestamp}</td></tr>"
            content += "</tbody></table><br><br>"

        return content


class RiskSummaryData(BaseModel):
    def __init__(
        self,
        raw_data,
        threat_unknown_indicators,
        threat_none_indicators,
        threat_low_indicators,
        threat_medium_indicators,
        threat_high_indicators,
        threat_critical_indicators,
        threat_total_indicators,
    ):
        super(RiskSummaryData, self).__init__(raw_data)
        self.threat_unknown_indicators = threat_unknown_indicators
        self.threat_none_indicators = threat_none_indicators
        self.threat_low_indicators = threat_low_indicators
        self.threat_medium_indicators = threat_medium_indicators
        self.threat_high_indicators = threat_high_indicators
        self.threat_critical_indicators = threat_critical_indicators
        self.threat_total_indicators = threat_total_indicators


class NewsData(BaseModel):
    def __init__(
        self,
        raw_data,
        news_title,
        news_channel,
        news_icon,
        news_link,
        news_timestamp,
    ):
        super(NewsData, self).__init__(raw_data)
        self.news_title = news_title
        self.news_channel = news_channel
        self.news_icon = news_icon
        self.news_link = news_link
        self.news_timestamp = news_timestamp

    def to_table(self):
        return {
            "title": self.news_title,
            "channel": self.news_channel,
            "link": self.news_link,
            "timestamp": self.news_timestamp,
        }


class Comment(BaseModel):
    def __init__(
        self,
        raw_data,
        comment_id,
        unique_id,
        user_comment,
        user_title,
        comment,
        date_added,
        date_updated,
    ):
        super(Comment, self).__init__(raw_data)
        self.comment_id = comment_id
        self.unique_id = unique_id
        self.user_comment = user_comment
        self.user_title = user_title
        self.comment = comment
        self.date_added = date_added
        self.date_updated = date_updated

    def to_table(self):
        return {
            "Date Added": self.date_added,
            "Data Updated": self.date_updated,
            "Comment": self.comment,
            "ID": self.comment_id,
        }
