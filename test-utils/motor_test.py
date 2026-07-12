import rclpy, time
from mavros_msgs.srv import CommandLong

rclpy.init()
node = rclpy.create_node('motor_test')
cli = node.create_client(CommandLong, '/mavros/cmd/command')
cli.wait_for_service()

def test_motor(motor, percent=10, seconds=3):
    req = CommandLong.Request()
    req.command = 209            # MAV_CMD_DO_MOTOR_TEST https://mavlink.io/en/messages/common.html#MAV_CMD_DO_MOTOR_TEST
    req.param1 = float(motor)    # motor instance number (1-8)
    req.param2 = 0.0             # throttle type - https://mavlink.io/en/messages/common.html#MOTOR_TEST_THROTTLE_TYPE
    req.param3 = float(percent)  # throttle %
    req.param4 = float(seconds)  # timeout
    
    fut = cli.call_async(req)

    rclpy.spin_until_future_complete(node, fut)
    print(f"motor {motor} ->", fut.result())
    
    time.sleep(seconds + 1)

test_motor(1)
test_motor(2)

node.destroy_node()
rclpy.shutdown()