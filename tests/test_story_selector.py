import os
import tempfile
import json
import time
from infrastructure.story_folder_storage import StoryFolderStorage
from main import StoryForgeApi


def test_list_stories_empty_when_no_base_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent = os.path.join(tmpdir, "NotExists")
        stories = StoryFolderStorage.list_stories(base_dir=non_existent)
        assert stories == []


def test_list_stories_scans_and_sorts_correctly():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 建立兩個故事資料夾，一早一晚
        story1_dir = os.path.join(tmpdir, "StoryA")
        os.makedirs(story1_dir, exist_ok=True)
        with open(os.path.join(story1_dir, "screenplay.json"), "w", encoding="utf-8") as f:
            json.dump([{"scene_id": 1}], f)

        time.sleep(0.02)

        story2_dir = os.path.join(tmpdir, "StoryB")
        os.makedirs(story2_dir, exist_ok=True)
        with open(os.path.join(story2_dir, "screenplay.json"), "w", encoding="utf-8") as f:
            json.dump([{"scene_id": 1}, {"scene_id": 2}], f)

        # 隨意資料夾（沒有 screenplay.json）不應被納入
        dummy_dir = os.path.join(tmpdir, "IgnoreMe")
        os.makedirs(dummy_dir, exist_ok=True)

        stories = StoryFolderStorage.list_stories(base_dir=tmpdir)
        assert len(stories) == 2
        # StoryB 較晚建立/修改，應排第一
        assert stories[0]["name"] == "StoryB"
        assert stories[0]["scene_count"] == 2
        assert stories[1]["name"] == "StoryA"
        assert stories[1]["scene_count"] == 1


def test_custom_folder_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_path = os.path.join(tmpdir, "my_custom_story")
        os.makedirs(custom_path, exist_ok=True)
        storage = StoryFolderStorage("任意名稱", folder_path=custom_path)
        assert storage.folder_path == custom_path
        assert storage.screenplay_path() == os.path.join(custom_path, "screenplay.json")


def test_api_load_screenplay_with_folder_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_path = os.path.join(tmpdir, "external_story")
        os.makedirs(custom_path, exist_ok=True)
        scenes = [{"scene_id": 1, "title": "外接場景", "lines": []}]
        with open(os.path.join(custom_path, "screenplay.json"), "w", encoding="utf-8") as f:
            json.dump(scenes, f)

        api = StoryForgeApi()
        res = api.load_screenplay("external_story", folder_path=custom_path)
        assert res.get("error") is None
        assert len(res["scenes"]) == 1
        assert res["story_name"] == "external_story"

        # 確認儲存進度時會使用自訂路徑
        api.save_screenplay_progress("external_story", [{"scene_id": 1}, {"scene_id": 2}])
        storage = api._get_storage("external_story")
        assert storage.folder_path == custom_path
        assert len(storage.load_screenplay()) == 2
