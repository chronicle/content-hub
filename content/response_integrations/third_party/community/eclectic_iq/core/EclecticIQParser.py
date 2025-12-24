from __future__ import annotations

import urllib.parse
from collections import defaultdict

from TIPCommon import add_prefix_to_dict, dict_to_flat


class EclecticIQLookupParser:
    def __init__(self, eiq_observables, eiq_entities, original_entities, eiq_url):
        self.eiq_observables = eiq_observables
        self.eiq_entities = eiq_entities
        self.original_entities = original_entities
        self.eiq_url = eiq_url

    def get_eiq_observable_value_map(self):
        return {obs.get("value"): obs for obs in self.eiq_observables}

    def get_eiq_observable_id_to_entity_map(self):
        eiq_entity_map = defaultdict(list)
        for entity in self.eiq_entities:
            for observable_url in entity.get("observables", []):
                obs_id = observable_url.split("observables/")[-1]
                eiq_entity_map[obs_id].append(entity)
        return eiq_entity_map

    def parse(self):
        parsed_data = {}
        eiq_observable_map = self.get_eiq_observable_value_map()
        eiq_entity_map = self.get_eiq_observable_id_to_entity_map()

        for entity in self.original_entities:
            identifier = str(entity.identifier.lower())
            eiq_observable = eiq_observable_map.get(identifier)
            if not eiq_observable or not eiq_observable.get("id"):
                continue

            observable_id = str(eiq_observable.get("id"))
            eiq_entities = eiq_entity_map.get(observable_id, [])

            parsed_data[entity.identifier] = {
                "eiq_observable": eiq_observable,
                "eiq_entities": eiq_entities,
            }
        return parsed_data

    def convert_eiq_observable_url(self, obs_type, obs_value):
        quote_value = urllib.parse.quote(obs_value)
        return f"{self.eiq_url}/observables/{obs_type}/{quote_value}"

    def convert_eiq_entity_url(self, entity_id):
        return f"{self.eiq_url}/entity/{entity_id}"

    def parse_as_enrichment(self):
        results = {}
        parsed_data = self.parse()
        for identifier, eiq_object in parsed_data.items():
            eiq_obs, eiq_entities = (
                eiq_object["eiq_observable"],
                eiq_object["eiq_entities"],
            )

            parsed_entites = []
            for entity in eiq_entities:
                parsed_entites.append(
                    {
                        "created_at": entity.get("created_at"),
                        "description": entity.get("data", {}).get("description"),
                        "title": entity.get("data", {}).get("title"),
                        "sources": entity.get("sources", []),
                        "last_updated_at": entity.get("last_updated_at"),
                        "type": entity.get("data", {}).get("type"),
                        "tags": entity.get("meta", {}).get("tags", []),
                        "estimated_observed_time": entity.get("meta", {}).get(
                            "estimated_observed_time",
                        ),
                        "estimated_threat_start_time": entity.get("meta", {}).get(
                            "estimated_threat_start_time",
                        ),
                        "half_life": entity.get("meta", {}).get("half_life"),
                        "platform_link": self.convert_eiq_entity_url(entity.get("id")),
                    },
                )

            enrich_result = {
                "observable_type": eiq_obs.get("type"),
                "confidence": eiq_obs.get("meta", {}).get("maliciousness"),
                "created_at": eiq_obs.get("created_at"),
                "last_updated_at": eiq_obs.get("last_updated_at"),
                "observable_id": eiq_obs.get("id"),
                "entities": parsed_entites,
                "platform_link": self.convert_eiq_observable_url(
                    eiq_obs.get("type"),
                    eiq_obs.get("value"),
                ),
            }
            results[identifier] = enrich_result

        return results

    def parse_as_link(self):
        results = []
        parsed_data = self.parse_as_enrichment()
        for identifier, enrich_object in parsed_data.items():
            results.append([identifier, enrich_object.get("platform_link")])
        return results

    def parse_as_csv(self):
        results = {}
        parsed_data = self.parse_as_enrichment()
        for identifier, enrich_object in parsed_data.items():
            entities = enrich_object.pop("entities", [])
            data = []
            for entity in entities:
                data.append(
                    {
                        "observable_type": enrich_object.get("observable_type"),
                        "observable_confidence": enrich_object.get("confidence"),
                        "observable_created_at": enrich_object.get("created_at"),
                        "observable_last_updated_at": enrich_object.get(
                            "last_updated_at",
                        ),
                        "observable_id": enrich_object.get("observable_id"),
                        "observable_platform_link": enrich_object.get("platform_link"),
                        "entity_created_at": entity.get("created_at"),
                        "entity_description": entity.get("description"),
                        "entity_title": entity.get("title"),
                        "entity_sources": ", ".join(entity.get("sources", [])),
                        "entity_last_updated_at": entity.get("last_updated_at"),
                        "entity_type": entity.get("type"),
                        "entity_tags": ", ".join(entity.get("tags", [])),
                        "entity_estimated_observed_time": entity.get(
                            "estimated_observed_time",
                        ),
                        "entity_estimated_threat_start_time": entity.get(
                            "estimated_threat_start_time",
                        ),
                        "enoriginal_entity_maptity_half_life": entity.get("half_life"),
                        "entity_platform_link": entity.get("platform_link"),
                    },
                )
            results[identifier] = data
        return results

    def parse_as_entity(self, prefix="EIQ"):
        results = []
        parsed_data = self.parse_as_enrichment()
        original_entity_map = {
            entity.identifier: entity for entity in self.original_entities
        }
        for identifier, enrich_object in parsed_data.items():
            enrich_object["entities"] = ", ".join(
                entity.get("platform_link")
                for entity in enrich_object.get("entities", [])
                if entity.get("platform_link")
            )
            enrichment_data = {
                k: v for k, v in enrich_object.items() if v not in (None, "")
            }
            data = dict_to_flat(enrichment_data)
            if prefix:
                data = add_prefix_to_dict(data, prefix)

            entity = original_entity_map.get(identifier)
            if entity and data:
                entity.additional_properties.update(data)
                entity.is_enriched = True
                results.append(entity)
        return results

    def missing_entities(self):
        original_entity_map = [entity.identifier for entity in self.original_entities]
        parsed_data = self.parse_as_enrichment()
        enriched_entities = set(parsed_data.keys())
        result = []
        for entity in self.original_entities:
            if entity.identifier not in enriched_entities:
                result.append(entity.identifier)
        return result
