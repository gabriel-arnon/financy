alter table classification_rules
  add column if not exists conditions jsonb,
  add column if not exists condition_logic text not null default 'all',
  add column if not exists actions jsonb,
  add column if not exists rule_version integer not null default 1;

alter table classification_rules
  drop constraint if exists classification_rules_condition_logic_check;

alter table classification_rules
  add constraint classification_rules_condition_logic_check
  check (condition_logic in ('all', 'any'));

create index if not exists classification_rules_conditions_gin_idx
  on classification_rules using gin (conditions)
  where conditions is not null;
