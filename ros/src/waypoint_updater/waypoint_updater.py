#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
import numpy as np
import math
from scipy.spatial import KDTree

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 200 # Number of waypoints we will publish. You can change this number
MAX_DECEL = .5      # [m/s2]

class WaypointUpdater(object):
    def __init__(self):
        rospy.init_node('waypoint_updater')

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)
        #rospy.Subscriber('/traffic_waypoint', Int32, self.traffic_cb)

        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

        # TODO: Add other member variables you need below
        self.stopline_wp_idx = -1
        self.pose = None
        self.base_waypoints = None      # base waypoints are the course map
        self.waypoints_2d = None        # base waypoints in (x,y) coordinates format 
        self.waypoint_tree = None       # base waypoints in KD tree format
        
        self.loop() 

        #rospy.spin()

    def loop(self):
        """
        This Node's Main Loop: It runs forever at 50Hz until ROS is shutdown. 
        """
        rate = rospy.Rate(50)
        while not rospy.is_shutdown():
            if self.pose and self.base_waypoints:
                # Get closest waypoint index
                closest_waypoint_idx = self.get_closest_waypoint_idx()
                # Publishes to final_waypoints from closest waypoint to closest waypoint + LOOKAHEAD_WPS
                self.publish_waypoints(closest_waypoint_idx)
            rate.sleep() 

    def get_closest_waypoint_idx(self):
        """
        Gets the closest waypoint index in front of the current car's pose. 
        To determine if the closest waypoint is in front, a dot product is used as verification
        """
        x = self.pose.pose.position.x
        y = self.pose.pose.position.y
        closest_idx = self.waypoint_tree.query([x, y], 1)[1] # first 1 is the closest item from (x,y), [0] refers to its distance, [1] refers to its index in tree
        
        # Check if closest is ahead or behind vehicle
        closest_coord = self.waypoints_2d[closest_idx]
        prev_coord    = self.waypoints_2d[closest_idx-1] 
        
        # Equation for hyperplane through closest_coords
        cl_vect   = np.array(closest_coord)
        prev_vect = np.array(prev_coord)
        pos_vect  = np.array([x, y])
        
        val= np.dot(cl_vect-prev_vect, pos_vect-cl_vect) 
        if val > 0:
            closest_idx = (closest_idx + 1) % len(self.waypoints_2d)
        
        return closest_idx 

    def publish_waypoints(self, closest_idx):
        """
        Creates a subset from base_waypoints from closest waypoint to closest waypoint + LOOKAHEAD_WPS.
        Publishes as a Lane msg type the subset to final_waypoints topic.
        """
        lane = Lane()
        lane.header  = self.base_waypoints.header
        farthest_idx = closest_idx + LOOKAHEAD_WPS
        lane.waypoints = self.base_waypoints.waypoints[closest_idx:farthest_idx]
        self.final_waypoints_pub.publish(lane) 

    def generate_lane(sef):
        lane - Lane() 
        closest_idx = self.get_closest_waypoint_idx()
        farthest_idx = closest_idx + LOOKAHEADWPS
        roi_waypoints = self.base_waypoints.waypoints[closest_idx:farthest_idx]
        
        if self.stopline_wp_idx == -1 or (self.stopline_wp_idx >= farthest_idx):
            lane.waypoints = roi_waypoints
        else:
            lane.waypoints = self.decelerate_waypoints(roi_waypoints, closest_idx)
        return lane 

    def decelerate_waypoints(self, waypoints, closest_idx):
        temp = []
        for i, wp in enumerate(waypoints): 
            p = Waypoint()
            p.pose = wp.pose 
            stop_idx = max(self.stopline_wp_idx - closest_idx - 2, 0) # two or three waypoints back from line so that the nose of the car stops before the line and not the center of car
            dist = self.distance(waypoints, i, stop_idx)
            vel = math.sqrt(2*MAX_DECEL*dist)
            if vel < 1.:
                vel = 0.
            p.twist.twist.linear.x = min(vel, wp.twist.twist.linear.x)
            temp.append(p)
            
        return temp


    def pose_cb(self, msg):
        """
        Callback function from subscriber to current_pose topic. It stores the current car's pose.
        """
        # TODO: Implement
        self.pose = msg

    def waypoints_cb(self, waypoints):
        """
        This is a special subscriber call back function that only runs once since input data never changes.
        it stores the waypoints in base_waypoints and provides two 2D coordinate system alternatives.
        waypoints_2D contains the (x,y) coordinates in a list and waypoint_tree in a KDTree data structure
        for a faster search. 
        """
        # TODO: Implement
        self.base_waypoints = waypoints
        if not self.waypoints_2d:
            self.waypoints_2d = [[waypoint.pose.pose.position.x, waypoint.pose.pose.position.y] for waypoint in waypoints.waypoints]
            self.waypoint_tree = KDTree(self.waypoints_2d)

    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
        self.stopline_wp_idx = msg.data

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
