import json
import re
import time

from UI.scripts.agents.core.paths import PathResolver


class WeeboMemory:
    def __init__(self, resolver: PathResolver):
        self.resolver = resolver

        self.storage_path = (
            self.resolver.spaceship_root
            / "UI"
            / "scripts"
            / "agents"
            / "persistence"
        )

        self.notes_file = self.storage_path / "notes.json"
        self.tasks_file = self.storage_path / "tasks.json"
        self.sessions_path = self.storage_path / "sessions"

        self.session_id = time.strftime("%Y%m%d-%H%M%S")
        self.session_file = self.sessions_path / f"{self.session_id}.jsonl"

        self._ensure_storage()

    def _ensure_storage(self):
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.sessions_path.mkdir(parents=True, exist_ok=True)

        for file_path in (self.notes_file, self.tasks_file):
            if not file_path.exists():
                file_path.write_text("[]", encoding="utf-8")

    def _now(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def _keywords(self, text):
        words = re.findall(r"[a-z0-9_]+", str(text).lower())
        return sorted({word for word in words if len(word) > 2})

    def _read(self, file_path):
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write(self, file_path, data):
        file_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def log_event(self, event_type, payload=None):
        event = {
            "ts": self._now(),
            "type": event_type,
            "payload": payload or {},
        }

        with open(self.session_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")

    def remember(self, note):
        notes = self._read(self.notes_file)
        now = self._now()

        notes.append(
            {
                "id": len(notes) + 1,
                "type": "note",
                "ts": now,
                "created_at": now,
                "note": note,
                "keywords": self._keywords(note),
            }
        )

        self._write(self.notes_file, notes)
        self.log_event("remember", {"note": note})

    def recall(self):
        return self._read(self.notes_file)

    def todo(self, task):
        tasks = self._read(self.tasks_file)
        now = self._now()

        tasks.append(
            {
                "id": len(tasks) + 1,
                "type": "task",
                "task": task,
                "status": "PENDING",
                "ts": now,
                "created_at": now,
                "updated_at": now,
                "keywords": self._keywords(task),
            }
        )

        self._write(self.tasks_file, tasks)
        self.log_event("todo", {"task": task})

    def get_tasks(self):
        return self._read(self.tasks_file)

    def complete_task(self, task_id):
        tasks = self._read(self.tasks_file)
        found = False

        for task in tasks:
            if str(task.get("id")) == str(task_id):
                task["status"] = "DONE"
                task["updated_at"] = self._now()
                task["completed_at"] = task["updated_at"]
                found = True
                break

        if found:
            self._write(self.tasks_file, tasks)
            self.log_event("complete_task", {"task_id": str(task_id)})

        return found

    def retrieve(self, query, limit=5):
        query_terms = set(self._keywords(query))

        if not query_terms:
            return {"notes": [], "tasks": []}

        scored_notes = []
        for note in self.recall():
            text = note.get("note", "")
            terms = set(note.get("keywords") or self._keywords(text))
            score = len(query_terms & terms)

            if score:
                scored_notes.append((score, note.get("ts", ""), note))

        scored_tasks = []
        for task in self.get_tasks():
            text = task.get("task", "")
            terms = set(task.get("keywords") or self._keywords(text))
            score = len(query_terms & terms)

            if score:
                if task.get("status") == "PENDING":
                    score += 1
                scored_tasks.append((score, task.get("ts", ""), task))

        scored_notes.sort(key=lambda item: (item[0], item[1]), reverse=True)
        scored_tasks.sort(key=lambda item: (item[0], item[1]), reverse=True)

        return {
            "notes": [item[2] for item in scored_notes[:limit]],
            "tasks": [item[2] for item in scored_tasks[:limit]],
        }

    def build_context(self, query, limit=4):
        relevant = self.retrieve(query, limit=limit)

        lines = [
            "MEMORY CONTEXT",
            "The following are remembered facts. These are NOT files and are NOT tool targets.",
            "",
        ]

        if relevant["notes"]:
            lines.append("Remembered notes:")
            for note in relevant["notes"]:
                lines.append(
                    f"  [{note.get('ts', 'unknown')}] {note.get('note', '')}"
                )
        else:
            lines.append("Remembered notes: none")

        lines.append("")

        if relevant["tasks"]:
            lines.append("Pending tasks:")
            for task in relevant["tasks"]:
                lines.append(
                    f"  [{task.get('status', 'UNKNOWN')}] "
                    f"#{task.get('id', '?')}: {task.get('task', '')}"
                )
        else:
            lines.append("Pending tasks: none")

        return "\n".join(lines)