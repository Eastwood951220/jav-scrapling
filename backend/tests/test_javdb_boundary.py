def test_javdb_boundary_exports_existing_parser_functions():
    from shared.integrations.content_sources.javdb import parse_page_section_name

    assert callable(parse_page_section_name)


def test_content_source_provider_protocol_imports():
    from shared.integrations.content_sources.javdb.provider import ContentSourceProvider, JavDbProvider

    assert ContentSourceProvider is not None
    assert JavDbProvider is not None
