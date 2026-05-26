-- v1.3.7.11: add lift_name_linked to masterlist_lt, lmd_ips to masterlist_lss
ALTER TABLE masterlist_lt ADD COLUMN lift_name_linked TEXT DEFAULT '';
ALTER TABLE masterlist_lss ADD COLUMN lmd_ips TEXT DEFAULT '';
