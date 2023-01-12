from .constants import *
from .mapping import add_prefix, add_mapping, add_inverse_prefix, get_non_asserted_mappings, merge_mapping_section_by_key
from .source import get_initial_sources, add_source, generate_database_connections, add_table, add_inverse_source
from .subject import add_subject, add_inverse_subject
from .predicateobject import add_predicate_object_maps, add_inverse_pom
import rdflib
import ruamel.yaml as yaml
from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO
import sys

def translate(yarrrml_data, mapping_format=RML_URI):
    logger.info("Translating YARRRML mapping to [R2]RML")

    list_initial_sources = get_initial_sources(yarrrml_data)
    rml_mapping = [add_prefix(yarrrml_data)]
    rml_mapping.extend(generate_database_connections(yarrrml_data, list_initial_sources))
    try:
        mappings, mapping_format = get_non_asserted_mappings(yarrrml_data,  dict.fromkeys(list(yarrrml_data.get(YARRRML_MAPPINGS).keys())), mapping_format)
        for mapping in yarrrml_data.get(YARRRML_MAPPINGS):
            if mapping_format == R2RML_URI:
                source_list = add_table(yarrrml_data, mapping, list_initial_sources)
            else:
                source_list = add_source(yarrrml_data, mapping, list_initial_sources)
            subject_list = add_subject(yarrrml_data, mapping, mapping_format)
            pred = add_predicate_object_maps(yarrrml_data, mapping, mapping_format)
            it = 0
            for source in source_list:
                for subject in subject_list:
                    map_aux = add_mapping(mapping, mappings, it)
                    if type(source) is list:
                        rml_mapping.append(map_aux + source[0] + subject + pred + source[1])
                    else:
                        rml_mapping.append(map_aux + source + subject + pred)
                    rml_mapping[len(rml_mapping) - 1] = rml_mapping[len(rml_mapping) - 1][:-2]
                    rml_mapping.append(".\n\n\n")
                    it = it + 1

        logger.info("RML content is created!")
        rml_mapping_string = "".join(rml_mapping)
        try:
            graph = rdflib.Graph()
            graph.parse(data=rml_mapping_string, format="turtle")
            logger.info("Mapping has been syntactically validated.")
        except Exception as e:
            logger.error("ERROR: There is a syntactic error in the generated mapping")
            logger.error(str(e))
            return None
    except Exception as e:
        logger.error("ERROR: The YARRRML mapping has not been translated")
        logger.error(str(e))
        return None

    logger.info("Translation has finished successfully.")

    return rml_mapping_string


def inverse_translation(rdf_mapping, mapping_format=RML_URI):
    yarrrml_mapping = {YARRRML_PREFIXES: {}, YARRRML_MAPPINGS: {}}
    rdf_mapping.bind('rml', rdflib.term.URIRef(RML_URI))
    rdf_mapping.bind('rr', rdflib.term.URIRef(R2RML_URI))
    rdf_mapping.bind('ql', rdflib.term.URIRef(QL_URI))
    yarrrml_mapping[YARRRML_PREFIXES] = add_inverse_prefix(rdf_mapping)
    query = f'SELECT ?triplesMap WHERE {{ ?triplesMap {RDF_TYPE} {R2RML_TRIPLES_MAP} . }} '
    triples_map = [tm[rdflib.Variable('triplesMap')] for tm in rdf_mapping.query(query).bindings]

    for tm in triples_map:
        tm_name = tm.split("/")[-1]
        yarrrml_tm = {YARRRML_SOURCE: add_inverse_source(tm, rdf_mapping, mapping_format)}
        yarrrml_tm[YARRRML_SHORTCUT_SUBJECTS], classes = add_inverse_subject(tm, rdf_mapping)
        yarrrml_tm[YARRRML_SHORTCUT_PREDICATEOBJECT] = add_inverse_pom(tm, rdf_mapping, classes, yarrrml_mapping[YARRRML_PREFIXES])
        yarrrml_mapping[YARRRML_MAPPINGS][tm_name] = yarrrml_tm

    string_content = yaml.dump(yarrrml_mapping)
    return string_content

def merge_mappings(yarrrrml_list):
    combined_mapping = {YARRRML_MAPPINGS:{}}
    prefixes_list = []
    for mapping in yarrrrml_list:
            prefixes_list.append(mapping[YARRRML_PREFIXES])
    combined_mapping = combined_mapping | merge_mapping_section_by_key(YARRRML_PREFIXES, prefixes_list)

    triples_map_ids = yarrrrml_list[0][YARRRML_MAPPINGS].keys()
    for individual_id in triples_map_ids:
        mapping_content_list = []
        for mapping in yarrrrml_list:
            if individual_id in mapping[YARRRML_MAPPINGS]:
                mapping_content_list.append(mapping[YARRRML_MAPPINGS][individual_id])
        combined_mapping[YARRRML_MAPPINGS] = combined_mapping[YARRRML_MAPPINGS] | merge_mapping_section_by_key(individual_id, mapping_content_list)

    string_content = yaml.dump(combined_mapping)
    return string_content