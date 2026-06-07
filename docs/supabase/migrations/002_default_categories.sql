insert into categories (user_id, name)
values
  (null, 'Alimentação'),
  (null, 'Supermercado'),
  (null, 'Transporte'),
  (null, 'Moradia'),
  (null, 'Saúde'),
  (null, 'Educação'),
  (null, 'Lazer'),
  (null, 'Serviços'),
  (null, 'Assinaturas'),
  (null, 'Impostos'),
  (null, 'Outros')
on conflict do nothing;
