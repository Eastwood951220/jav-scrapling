"""Scan files step — list files in the download folder recursively."""


class ScanFilesStep:
    name = "scan_files"

    def is_completed(self, context) -> bool:
        return bool(context.task.get("scanned_files"))

    def execute(self, context) -> dict:
        task = context.task
        task_id = task["task_id"]
        download_path = task["download_path"]

        all_entries = context.provider.list_files(download_path)
        files = []
        for entry in all_entries:
            if entry.is_directory:
                try:
                    sub_entries = context.provider.list_files(entry.full_path)
                    files.extend(sub_entries)
                except Exception:
                    files.append(entry)
            else:
                files.append(entry)

        scanned = [
            {
                "name": f.name,
                "path": f.full_path,
                "size": f.size,
                "is_dir": f.is_directory,
            }
            for f in files
            if not f.is_directory
        ]

        context.task_repository.update(task_id, {"scanned_files": scanned})
        context.logger.log(f"扫描到 {len(scanned)} 个文件")

        return {**task, "scanned_files": scanned}
