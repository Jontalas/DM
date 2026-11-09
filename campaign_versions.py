"""Distinguish membership refreshes from actual changes to campaign state."""


def state_version(metadata):
    snapshot=metadata.get('snapshot')
    if isinstance(snapshot,str) and snapshot and metadata.get('stateVersionSnapshot')==snapshot:
        return metadata.get('stateVersion',metadata.get('version'))
    # Old writers replace the snapshot without updating our marker. Treat that
    # as a state change; never infer membership-only history from an old mark.
    return metadata.get('version')


def accepts_action(metadata,submitted):
    current=metadata.get('version')
    changed=state_version(metadata)
    return (type(submitted)==int and type(current)==int and type(changed)==int
            and 0<=changed<=submitted<=current)
