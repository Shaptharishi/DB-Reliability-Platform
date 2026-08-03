resource "aws_db_subnet_group" "default" {
  name       = "db-reliability-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name = "db-reliability-subnet-group"
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "db-reliability-postgres-tf"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = "testdb1"
  username               = "postgres"
  password               = var.postgres_password
  db_subnet_group_name   = aws_db_subnet_group.default.name
  vpc_security_group_ids = [aws_security_group.postgres_sg.id]
  publicly_accessible    = true
  skip_final_snapshot    = true
  backup_retention_period = 1

  tags = {
    Name = "db-reliability-postgres-tf"
  }
}

resource "aws_db_instance" "mysql" {
  identifier              = "db-reliability-mysql-tf"
  engine                  = "mysql"
  engine_version          = "8.0"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  storage_type            = "gp2"
  db_name                 = "testdb1"
  username                = "admin"
  password                = var.mysql_password
  db_subnet_group_name    = aws_db_subnet_group.default.name
  vpc_security_group_ids  = [aws_security_group.mysql_sg.id]
  publicly_accessible     = true
  skip_final_snapshot     = true
  backup_retention_period = 1

  tags = {
    Name = "db-reliability-mysql-tf"
  }
}

resource "aws_elasticache_subnet_group" "default" {
  name       = "db-reliability-cache-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "db-reliability-redis-tf"
  description                = "Single-node Valkey cache for DB reliability platform"
  engine                     = "valkey"
  node_type                  = "cache.t3.micro"
  num_cache_clusters         = 1
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.default.name
  security_group_ids         = [aws_security_group.redis_sg.id]
  transit_encryption_enabled = true
  automatic_failover_enabled = false

  tags = {
    Name = "db-reliability-redis-tf"
  }
}
