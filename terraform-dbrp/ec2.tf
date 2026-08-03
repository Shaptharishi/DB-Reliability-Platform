data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "collector" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  key_name               = "db-reliability-ec2-key"
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  subnet_id              = data.aws_subnets.default.ids[0]

  user_data_replace_on_change = true

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    postgres_host      = aws_db_instance.postgres.address
    postgres_password  = var.postgres_password
    mysql_host         = aws_db_instance.mysql.address
    mysql_password     = var.mysql_password
    redis_host         = aws_elasticache_replication_group.redis.primary_endpoint_address
    slack_webhook_url  = var.SLACK_WEBHOOK_URL
  })

  tags = {
    Name = "db-reliability-collector-tf"
  }
}

output "ec2_public_ip" {
  value = aws_instance.collector.public_ip
}