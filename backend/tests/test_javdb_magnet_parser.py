from scrapling.parser import Selector

from scraper.spiders.javdb.javdb_parser import parse_detail_page, parse_magnets


def test_parse_magnets_extracts_link_name_size_files_tags_and_date():
    page = Selector(
        """
        <div id="magnets-content">
          <div class="item">
            <div class="magnet-name">
              <a href="magnet:?xt=urn:btih:30bb559440d8f806eee3dc6e70e2f0911003d099">SSIS-889-C.torrent</a>
              <span class="meta">8.75GB, 1個文件</span>
              <span class="tags">
                <span class="tag">高清</span>
                <span class="tag">字幕</span>
              </span>
            </div>
            <button class="copy-to-clipboard" data-clipboard-text="magnet:?xt=urn:btih:truncated&dn=bad"></button>
            <div class="date"><span class="time">2023-10-01</span></div>
          </div>
          <div class="item">
            <div class="magnet-name">
              <a href="magnet:?xt=urn:btih:f80d722318e10560ff834feeb315794479186e05">ssis-889-4k.torrent</a>
              <span class="meta">28.88GB, 1個文件</span>
              <span class="tags"><span class="tag">高清</span></span>
            </div>
            <div class="date"><span class="time">2023-09-24</span></div>
          </div>
        </div>
        """
    )

    assert parse_magnets(page) == [
        {
            "magnet": "magnet:?xt=urn:btih:30bb559440d8f806eee3dc6e70e2f0911003d099",
            "name": "SSIS-889-C.torrent",
            "size": 8960.0,
            "size_text": "8.75GB",
            "file_count": 1,
            "file_text": "1個文件",
            "tags": ["高清", "字幕"],
            "has_chinese_sub": True,
            "date": "2023-10-01",
        },
        {
            "magnet": "magnet:?xt=urn:btih:f80d722318e10560ff834feeb315794479186e05",
            "name": "ssis-889-4k.torrent",
            "size": 29573.12,
            "size_text": "28.88GB",
            "file_count": 1,
            "file_text": "1個文件",
            "tags": ["高清"],
            "has_chinese_sub": False,
            "date": "2023-09-24",
        },
    ]


def test_parse_magnets_keeps_rows_with_only_name_and_file_metadata():
    page = Selector(
        """
        <div id="magnets-content">
          <div class="item">
            <div class="magnet-name">
              <span class="name">SSIS-889</span>
              <span class="meta">2.75GB, 20個文件</span>
            </div>
            <div class="date"><span class="time">2023-10-17</span></div>
          </div>
        </div>
        """
    )

    assert parse_magnets(page) == [
        {
            "magnet": "",
            "name": "SSIS-889",
            "size": 2816.0,
            "size_text": "2.75GB",
            "file_count": 20,
            "file_text": "20個文件",
            "tags": [],
            "has_chinese_sub": False,
            "date": "2023-10-17",
        }
    ]


def test_parse_detail_page_attaches_all_magnets_without_best_selection_fields():
    page = Selector(
        """
        <h2 class="title">SSIS-889 Title</h2>
        <nav class="movie-panel-info">
          <div class="panel-block"><strong>日期:</strong><span class="value">2023-10-17</span></div>
        </nav>
        <div id="magnets-content">
          <div class="item">
            <div class="magnet-name">
              <a href="magnet:?xt=urn:btih:30bb559440d8f806eee3dc6e70e2f0911003d099">SSIS-889-C.torrent</a>
              <span class="meta">8.75GB, 1個文件</span>
              <span class="tags"><span class="tag">字幕</span></span>
            </div>
            <div class="date"><span class="time">2023-10-01</span></div>
          </div>
        </div>
        """
    )

    detail = parse_detail_page(page)

    assert detail["title"] == "SSIS-889 Title"
    assert detail["release_date"] == "2023-10-17"
    assert detail["magnets"] == [
        {
            "magnet": "magnet:?xt=urn:btih:30bb559440d8f806eee3dc6e70e2f0911003d099",
            "name": "SSIS-889-C.torrent",
            "size": 8960.0,
            "size_text": "8.75GB",
            "file_count": 1,
            "file_text": "1個文件",
            "tags": ["字幕"],
            "has_chinese_sub": True,
            "date": "2023-10-01",
        }
    ]
    assert "magnet" not in detail
    assert "size" not in detail
    assert "has_chinese_sub" not in detail
