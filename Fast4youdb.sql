CREATE DATABASE IF NOT EXISTS food4you_db;
USE food4you_db;

-- =======================
-- TABELA DE USUÁRIOS
-- =======================
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    foto_url VARCHAR(255),
    is_admin TINYINT(1) DEFAULT 0
);

-- Tornar um usuário admin (caso exista)
UPDATE usuarios
SET is_admin = 1
WHERE email = 'admin@gmail.com';


-- =======================
-- TABELA DE RESTAURANTES
-- =======================
CREATE TABLE IF NOT EXISTS restaurantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    endereco VARCHAR(255),
    telefone VARCHAR(50),
    descricao TEXT,
    categoria VARCHAR(50) DEFAULT 'lanches',
    rating VARCHAR(10) DEFAULT '4.0',
    delivery_time VARCHAR(50) DEFAULT '20-30 min',
    delivery_fee VARCHAR(50) DEFAULT 'Grátis',
    tags TEXT,
    badge VARCHAR(100),
    image VARCHAR(255) DEFAULT '../static/imagens/default_restaurante.png'
);

-- Adicionar restaurante Burguer King automaticamente
INSERT INTO restaurantes 
(nome, endereco, telefone, descricao, categoria, rating, delivery_time, delivery_fee, tags, badge, image)
VALUES 
('Burguer king', 'endereço teste', '11976717289', 'Melhor restaurante', 'Lanches', '5', '10 min', '5', 'Mais pedido', 'Popular', '/static/imagens/restaurante_Burguer_king.png');


-- =======================
-- TABELA DE ASSINATURAS
-- =======================
CREATE TABLE IF NOT EXISTS assinaturas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    restaurante_id INT NOT NULL,
    plano VARCHAR(100) NOT NULL DEFAULT 'Plano básico',
    status VARCHAR(20) DEFAULT 'ativa',
    data_inicio DATE NOT NULL DEFAULT (CURRENT_DATE),
    proximo_pagamento DATE DEFAULT (CURRENT_DATE + INTERVAL 30 DAY),
    dia VARCHAR(20) NOT NULL,
    endereco VARCHAR(255) NOT NULL,
    metodo_pagamento VARCHAR(20) NOT NULL,
    detalhe_pagamento VARCHAR(255),

    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
);

-- =======================
-- TABELA DE AVALIAÇÕES
-- =======================
CREATE TABLE IF NOT EXISTS avaliacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    restaurante_id INT NOT NULL,
    estrelas INT NOT NULL CHECK (estrelas >= 1 AND estrelas <= 5),
    comentario TEXT,
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id)
);
