#!/bin/env python3
"""
A tool for tracking changed files and directories performing effective (if manual) replication
"""
import hashlib
import os
import sys
import tqdm


def is_dirty(data):
    """
    Checks if any changes in the filesystem are not in the hashdb, takes return of check, and returns a boolean value.
    """
    if len(data["additions"]) > 0:
        return True
    if len(data["deletions"]) > 0:
        return True
    if len(data["changes"]) > 0:
        return True
    return False

def write_db(sumfile,hashdb):
    """
    Write a hashdb into a checksum file.
    """
    with open(sumfile, "w") as file:
        for filename in hashdb.keys():
            filehash = hashdb[filename]
            file.write(f"{filehash}\t{filename}\n")

def make_parents(filepath):
    """
    Create directories to allow the creation of a file
    """
    (directory, filename) = os.path.split(filepath)
    while not os.path.exists(directory):
        os.mkdir(directory)
        (directory, _) = os.path.split(directory)

#directory = "/home/mz/archive/files/"
    
def load_db(sumfile):
    """
    Attempts to load the hashdatabase, proving an empty one if not found
    """
    # Attempt to load the hash database
    if os.path.exists(sumfile):
        hashdb = {}
        print("Reading checksum db...")
        with open(sumfile, "r") as fd:
            for line in fd.readlines():
                line = line.rstrip()
                (filehash, filename) = line.split("\t", maxsplit=1)
                hashdb[filename] = filehash
    else:
        hashdb = {}
        print("Cant find checksum file at ", sumfile)
        print("Warning, no checksums found, assuming zero known files!")
    return hashdb

def check(directory, log=True, tqdm=tqdm.tqdm):
    """
    Check for changes in a directory, returns the current hashdb, and changes in the file tree
    """
    # Checksums should be stored inside of the directory
    sumfile = os.path.join(directory, ".sha1sums")

    hashdb = load_db(sumfile)

    # Arrays for tracking file changes
    additions = []
    changes = []
    deletions = []


    if log:
        print("Getting filelist...")
    # For every file that is not the hash db
    filelist = set()
    for (root,dirs,files) in os.walk(directory):
        for file in [os.path.join(root, file) for file in files if not file.endswith(".sha1sums") and not file.endswith(".sha1sums_new")]:
            # Strip the path to the directory to ensure that filenames are stable
            fileref = os.path.relpath(file, start=directory)
            filelist.add(fileref)

    if log:
        print("Computing hashes, please wait...")

    if tqdm:
        progresslist = tqdm(filelist)
    else:
        progresslist = filelist
    
    for fileref in progresslist:
        file = os.path.join(directory, fileref)
        # Hash file
        filehash = hashlib.sha1()
        with open(file, "rb") as fd:
            while True:
                chunk = fd.read(1025 * 1024)
                filehash.update(chunk)
                if len(chunk) == 0:
                    break
        filehash = filehash.hexdigest()
        # Check database, adding to additions or changes
        if fileref in hashdb:
            if hashdb[fileref] != filehash:
                changes.append((fileref, filehash))

        else:
            additions.append((fileref, filehash))

    # Check for deletions
    for file in hashdb:
        if not file in filelist:
            deletions.append(file)

    return {
        "db": hashdb,
        "deletions": deletions,
        "additions": additions,
        "changes": changes
    }

def replicate(src, dst):
    import shutil
    """
    Intractive replication of clean file trees.
    """
    print("Checking source ", src)
    srcdata = check(src)
    print("Checking destination ", dst)
    dstdata = check(dst)
    

    if is_dirty(srcdata):
        print("* Source filetree is dirty, please run an integrity check and review changes")
        return
    
    if is_dirty(dstdata):
        print("* Destination filetree is dirty, please run an integrity check and review changes, this likly indicates damage to the backup")
        return

    newdsthash = dstdata["db"]

    for srcfile in srcdata["db"].keys():
        srchash = srcdata["db"][srcfile]
        dsthash = dstdata["db"].get(srcfile)
        if dsthash:
            if dsthash != srchash:
                print("File", srcfile, "changed in src filesystem, replicating.")
                srcpath = os.path.join(src, srcfile)
                dstpath = os.path.join(dst, srcfile)
                print(dstpath, "->", srcpath)
                shutil.copy2(srcpath, dstpath)
                newdsthash[srcfile] = srchash
        else:
            print("File", srcfile, "added in src filesystem, replicating.")
            srcpath = os.path.join(src, srcfile)
            dstpath = os.path.join(dst, srcfile)
            print(dstpath, "->", srcpath)
            make_parents(dstpath)
            newdsthash[srcfile] = srchash
            shutil.copy2(srcpath, dstpath)
    
    for dstfile in newdsthash:
        if not srcdata["db"].get(dstfile):
            print("* Refusing to automaticly delete ", dstfile, " in backup")

    write_db(os.path.join(dst, ".sha1sums"), newdsthash)

def interactive_check(directory):
    sumfile = os.path.join(directory, ".sha1sums")
    
    results = check(directory)
    additions = results["additions"]
    deletions = results["deletions"]
    changes = results["changes"]
    hashdb = results["db"]

    # Show statistics
    print(f"{len(additions)} Additions, {len(deletions)} Deletions, {len(changes)} Changes.")

    for (file, filehash) in additions:
        print("File added:")
        print("\t", file)
        print("\t", filehash)

    for (file, filehash) in changes:
        print("File CHANGED:")
        print("\t", file)
        print("\t", hashdb[file], "->",filehash)

    for (file) in deletions:
        print("File DELETED:")
        print("\t", file)
        print("\t", hashdb[file])

    print("* Please review changes, including checking if changed files are ok before commiting.")
    commit = input("Commit changes [y/n]? ")
    if not (commit.startswith("y") or commit.startswith("Y")):
        print("Canceled.")
        exit(0)

    # Change database to reflect file system state
    for (name, filehash) in additions:
        hashdb[name] = filehash

    for (name, filehash) in changes:
        hashdb[name] = filehash

    for (name) in deletions:
        del hashdb[name]
    
    write_db(sumfile, hashdb)


if __name__ == "__main__":
    def usage():
        print(f"Usage: {sys.argv[0]} check [directory]")
        print(f"Usage: {sys.argv[0]} replicate [src] [dst]")

    if len(sys.argv) < 2:
        usage()
        exit(1)
    subcommand = sys.argv[1]
    
    if subcommand == "check":
        if len(sys.argv) < 3:
            usage()
            exit(1)
        directory = sys.argv[2]
        interactive_check(directory)
    elif subcommand == "replicate":
        if len(sys.argv) < 4:
            usage()
            exit(1)
        src = sys.argv[2]
        dst = sys.argv[3]
        replicate(src, dst)
    else:
        print("Unrecognize subcommand ", sumcommand)
        usage()
        exit(1)


