"""Guard against invalid/duplicate MediaStore rows in category listings.

Deduplicate only after validating the row and category: a malformed entry must
not hide a later valid entry with the same MediaStore ID.
"""
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "app/src/main/java/dev/xarkon/link/FileBrowserActivity.java"


class MediaIdTests(unittest.TestCase):
    def query_source(self):
        text = SOURCE.read_text(encoding="utf-8")
        return text.split(
            "private ArrayList<Entry> queryMedia(int cat,String prefix,boolean complete,CancellationSignal cancellation)",
            1,
        )[1].split("private static final class MediaGrouping", 1)[0]

    def test_unique_positive_media_ids(self):
        query = self.query_source()
        self.assertIn("HashSet<Long> seenMediaIds=new HashSet<>()", query)
        self.assertIn("if(c.isNull(0))continue;", query)
        self.assertIn("catch(RuntimeException malformedId){continue;}", query)
        self.assertIn("if(mediaId<=0)continue;", query)
        self.assertIn("if(!seenMediaIds.add(mediaId))continue;", query)
        self.assertIn("ContentUris.withAppendedId(base,mediaId)", query)
        self.assertLess(query.index("if(mediaId<=0)continue;"), query.index("seenMediaIds.add(mediaId)"))
        self.assertLess(query.index("seenMediaIds.add(mediaId)"), query.index("++scanned>MAX_MEDIA_SCAN"))

    def test_invalid_media_does_not_hide_valid_duplicate_id(self):
        query = self.query_source()
        self.assertLess(
            query.index("BrowserMediaQuery.matches(path,normalizedPrefix)"),
            query.index("seenMediaIds.add(mediaId)"),
        )
        self.assertLess(
            query.index("BrowserCategoryFilter.accepts(cat,name,mime)"),
            query.index("seenMediaIds.add(mediaId)"),
        )
        self.assertLess(
            query.index("hiddenPath(name)||hiddenPath(path)"),
            query.index("seenMediaIds.add(mediaId)"),
        )


if __name__ == "__main__":
    unittest.main()
