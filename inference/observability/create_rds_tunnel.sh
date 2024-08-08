#!/bin/bash
if [ -z "$1" ]
  then
      echo "Please supply the absolute path to the **private** key you used to set up the EC2 instance"
      exit 1
fi

instance_id=$(aws ec2 describe-instances --filters 'Name=tag:Name,Values=bastion*'  --filters Name=instance-state-name,Values=running --output text --query 'Reservations[*].Instances[*].InstanceId')
echo $instance_id
dbinstance_address=$(aws rds describe-db-instances --filters 'Name=db-instance-id,Values=droughtwatch' --output json | jq -r .DBInstances[0].Endpoint.Address)
cmd="ssh -i $1 ubuntu@${instance_id} -o ServerAliveInterval=30 -o ProxyCommand='aws ec2-instance-connect open-tunnel --instance-id ${instance_id}' -L 5432:${dbinstance_address}:5432"
echo $cmd
