-- LSS MasterList: per-block network/IP data derived from LSS - MasterList.xlsx
-- Match key: postal_code (LSS) ↔ postcode (TMS records)
CREATE TABLE IF NOT EXISTS masterlist_lss (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    postal_code TEXT    NOT NULL,
    lmd_ip      TEXT,
    proxy_ip    TEXT,
    vp_tun_ip   TEXT,
    lmd_tun_ip  TEXT,
    dvr_ip      TEXT,
    UNIQUE (postal_code)
);
