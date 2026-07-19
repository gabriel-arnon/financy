insert into categories (user_id, name, type, status, is_system)
values
  (null, 'Juros e dividendos', 'income', 'active', true),
  (null, 'Uber e apps', 'expense', 'active', true),
  (null, 'Delivery', 'expense', 'active', true),
  (null, 'Gasolina', 'expense', 'active', true)
on conflict (name) where user_id is null do update set
  type = excluded.type,
  status = 'active',
  is_system = true;
