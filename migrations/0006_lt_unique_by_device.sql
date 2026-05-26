-- v1.3.7.11 fix: change masterlist_lt unique key from (tc,pfx,block) to
-- (tc,pfx,block,lmd_device_id) so blocks with multiple LMD devices can
-- store one row per device instead of collapsing to a single row.
CREATE TABLE masterlist_lt_new (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tc               TEXT NOT NULL,
    pfx              TEXT NOT NULL,
    block            TEXT NOT NULL,
    town_council     TEXT,
    full_add         TEXT,
    postal_code      TEXT,
    lift_names_all   TEXT,
    lift_name_linked TEXT DEFAULT '',
    interface        TEXT,
    lss              TEXT,
    lmd_device_id    TEXT DEFAULT '',
    UNIQUE (tc, pfx, block, lmd_device_id)
);

INSERT INTO masterlist_lt_new
    (tc, pfx, block, town_council, full_add, postal_code,
     lift_names_all, lift_name_linked, interface, lss, lmd_device_id)
SELECT tc, pfx, block, town_council, full_add, postal_code,
       lift_names_all, lift_name_linked, interface, lss, lmd_device_id
FROM masterlist_lt;

DROP TABLE masterlist_lt;

ALTER TABLE masterlist_lt_new RENAME TO masterlist_lt;
