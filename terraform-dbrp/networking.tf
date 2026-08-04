# ---- Look up existing default VPC and subnets ----

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ---- Security group for the EC2 instance ----

resource "aws_security_group" "ec2_sg" {
  name        = "db-reliability-ec2-sg-tf"
  description = "Allows SSH, Grafana, and self-referencing DB access"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH - key auth only, open for GitHub Actions CI/CD"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Grafana from my IP"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.my_ip.response_body)}/32"]
  }

  ingress {
    description = "ClickHouse HTTP from my IP"
    from_port   = 8123
    to_port     = 8123
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.my_ip.response_body)}/32"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "db-reliability-ec2-sg-tf"
  }
}

# ---- Fetch your current public IP automatically ----

data "http" "my_ip" {
  url = "https://ifconfig.me/ip"
}