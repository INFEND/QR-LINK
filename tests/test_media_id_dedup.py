"""Guard against invalid/duplicate MediaStore rows in category listings."""
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/"app/src/main/java/dev/xarkon/link/FileBrowserActivity.java"

class MediaIdTests(unittest.TestCase):
    def test_unique_positive_media_ids(self):
        text=SOURCE.read_text(encoding="utf-8")
        query=text.split("private ArrayList<Entry> queryMedia(int cat,String prefix,boolean complete,CancellationSignal cancellation)",1)[1].split("private static final class MediaGrouping",1)[0]
        self.assertIn("HashSet<Long> seenMediaIds=new HashSet<>()",query)
        self.assertIn("if(c.isNull(0))continue;",query)
        self.assertIn("if(mediaId<=0||!seenMediaIds.add(mediaId))continue;",query)
        self.assertIn("ContentUris.withAppendedId(base,mediaId)",query)
        self.assertLess(query.index("seenMediaIds.add(mediaId)"),
                        query.index("++scanned>MAX_MEDIA_SCAN"))
