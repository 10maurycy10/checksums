# File checksum

  Backups are a great way to avoid data-loss, but detecting more subtle dataloss is important.
This dataloss can be bitrot, random bit flips that occur as storage ages, or accidental overwriting or deletions of a file.
Tools like RAID and ZFS protect against bit rot, but not accidental overwriting of data.
The simplest way to prevent dataloss by accidental overwriting, filesystem hiccups, or bit rot is to simply have multiple redundant copies on different drives.
In theory this provides very good protection, but it is equally important to detect damaged files so that they don't go unnoticed, or worse, get replicated over the remaining good copies.

  This is a task commonly accomplished with checksums, using a tool like `sha1sum`, but this makes replication hard and offers no way to keep the file up to date with the filesystem.
This tool creates a database of checksums for files in a directory, and keeps it up to date with the data, allowing the user to review any changes detected.
It also allows replication of the directory, with updating and integrity checking.

## Limitations

- Newlines in filenames are not supported and will break things.
- File permission and ownership is not checked.
- Integrity checking and replication requires user interaction.

## Usage

  The `check` subcommands creates a hash database in the directory under `.sha1sums`.
If such a database already exists, it will display a list of changed, added, or deleted files and if the user confirms, it will update the hashdb.
Manually checking modified files is recommended to ensure that they are ok.

```sh
freeze.py check [directory]
```

  The replicate command copies data from one directory to another.
It first ensure that the data has not changed from the hash database, it will exit (with a non zero exit code) if any differences are found.
Finally it copies any files that differ between `src` and `dst`.

```sh
freeze.py replicate [src] [dst]
```

  It wont delete files from `dst` even if they have been removed from `src`, it will instead log a message to console.
If you want to remove these files from the backup, remove them manual and run the check subcommand on `dst`.

