insert into categories (user_id, name, type, status, is_system)
values
  (null, 'Alimentação', 'expense', 'active', true),
  (null, 'Supermercado', 'expense', 'active', true),
  (null, 'Transporte', 'expense', 'active', true),
  (null, 'Moradia', 'expense', 'active', true),
  (null, 'Saúde', 'expense', 'active', true),
  (null, 'Educação', 'expense', 'active', true),
  (null, 'Lazer', 'expense', 'active', true),
  (null, 'Serviços', 'expense', 'active', true),
  (null, 'Assinaturas', 'expense', 'active', true),
  (null, 'Impostos', 'expense', 'active', true),
  (null, 'Juros e dividendos', 'income', 'active', true),
  (null, 'Uber e apps', 'expense', 'active', true),
  (null, 'Delivery', 'expense', 'active', true),
  (null, 'Gasolina', 'expense', 'active', true),
  (null, 'Outros', 'both', 'active', true)
on conflict do nothing;
