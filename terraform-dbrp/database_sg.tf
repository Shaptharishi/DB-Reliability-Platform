# ---- PostgreSQL security group ----

resource "aws_security_group" "postgres_sg" {
  name        = "db-reliability-postgres-sg-tf"
  description = "Allows PostgreSQL access from EC2 and my IP"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "PostgreSQL from EC2 instance"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  ingress {
    description = "PostgreSQL from my IP for direct testing"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.my_ip.response_body)}/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "db-reliability-postgres-sg-tf"
  }
}

# ---- MySQL security group ----

resource "aws_security_group" "mysql_sg" {
  name        = "db-reliability-mysql-sg-tf"
  description = "Allows MySQL access from EC2 and my IP"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "MySQL from EC2 instance"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  ingress {
    description = "MySQL from my IP for direct testing"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.my_ip.response_body)}/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "db-reliability-mysql-sg-tf"
  }
}

# ---- Redis/Valkey security group ----

resource "aws_security_group" "redis_sg" {
  name        = "db-reliability-redis-sg-tf"
  description = "Allows Redis/Valkey access from EC2 and itself"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Redis from EC2 instance"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  ingress {
    description = "Redis from my IP for direct testing"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.my_ip.response_body)}/32"]
  }

  ingress {
    description = "Allow Redis members to reach each other"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "db-reliability-redis-sg-tf"
  }
}