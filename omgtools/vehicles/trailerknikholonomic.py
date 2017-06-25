# This file is part of OMG-tools.
#
# OMG-tools -- Optimal Motion Generation-tools
# Copyright (C) 2016 Ruben Van Parys & Tim Mercy, KU Leuven.
# All rights reserved.
#
# OMG-tools is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
from vehicle import Vehicle
from holonomicorient import HolonomicOrient
from ..basics.shape import Circle, Rectangle, Square
from ..basics.spline_extra import sample_splines
from casadi import inf
import numpy as np

# splines = [tg_ha_tr, x, y, tg_ha_veh]
# state=[x_tr, y_tr, theta_tr, x_veh, y_veh, theta_veh]
# input = [dx, dy, dtheta_veh]

class TrailerKnikHolonomic(Vehicle):
    #####
    def __init__(self, lead_veh=None, shapes=Circle(0.2), l_hitch=0.2, l_hitch1=0.2, options=None, bounds=None):
        # een tweede lengte invoegen van hitch: stuk tussen middelpunt van het voertuig en trekhaak en een stuk tussen trekhaak en trailer.
        #####
        bounds = bounds or {}
        Vehicle.__init__(
            self, n_spl=1 + lead_veh.n_spl, degree=3, shapes=shapes, options=options)
        # n_spl contains all splines of lead_veh and trailer
        # being: tg_ha_trailer, v_til_veh, tg_ha_veh -> in latex respectievelijk: r_1, w_0, r_0
        self.lead_veh = HolonomicOrient() if (lead_veh is None) else lead_veh  # vehicle which pulls the trailer
        self.l_hitch = l_hitch  # tussen middelpunt voertuig en hitchpunt
        #####
        self.l_hitch1 = l_hitch1  # tussen hitchpunt en middelpunt trailer
        #####
        self.tmax = bounds['tmax'] if 'tmax' in bounds else 45.  # limit angle between trailer and vehicle
        self.tmin = bounds['tmin'] if 'tmin' in bounds else -45.


    def set_default_options(self):
        Vehicle.set_default_options(self)

    def init(self):
        self.lead_veh.init()

    def define_trajectory_constraints(self, splines):
        T = self.define_symbol('T')
        tg_ha_tr, x,y, tg_ha_veh = splines
        dtg_ha_tr, v_x, v_y, dtg_ha_veh = tg_ha_tr.derivative(),x.derivative(),y.derivative(), tg_ha_veh.derivative()

        # change in orientation of the trailer is due to velocity of vehicle
        # relaxed this equality constraint with eps
        eps = 1e-3

        self.define_constraint((self.l_hitch1 * 2 * dtg_ha_tr + 2 * tg_ha_tr * v_x - (1 - tg_ha_tr ** 2) * v_y) * ( 1 + tg_ha_veh ** 2) ** 2 +
                               2 * dtg_ha_veh * self.l_hitch * ( 4 * tg_ha_tr * tg_ha_veh + (1 - tg_ha_tr ** 2) * (1 - tg_ha_veh ** 2)) - (1 + tg_ha_veh ** 2) ** 2 * T * eps,-inf, 0.)
        self.define_constraint(-(self.l_hitch1 * 2 * dtg_ha_tr + 2 * tg_ha_tr * v_x - (1 - tg_ha_tr ** 2) * v_y) * (
        1 + tg_ha_veh ** 2) ** 2 - 2 * dtg_ha_veh * self.l_hitch * (
                               4 * tg_ha_tr * tg_ha_veh + (1 - tg_ha_tr ** 2) * (1 - tg_ha_veh ** 2)) - (
                               1 + tg_ha_veh ** 2) ** 2 * T * eps, -inf, 0.)
        # limit angle between vehicle and trailer
        self.define_constraint(tg_ha_veh - tg_ha_tr - np.tan(np.radians(self.tmax) / 2.), -inf, 0.)
        self.define_constraint(-tg_ha_veh + tg_ha_tr + np.tan(np.radians(self.tmin) / 2.), -inf, 0.)
        # call lead_veh trajectory constraints
        self.lead_veh.define_trajectory_constraints(splines[1:])

    def get_initial_constraints(self, splines):
        # trailer has a certain theta0 --> trailer position follows from this
        T = self.define_symbol('T')
        tg_ha_tr0 = self.define_parameter('tg_ha_tr0', 1)
        dtg_ha_tr0 = self.define_parameter('dtg_ha_tr0', 1)
        tg_ha_tr = splines[0]
        dtg_ha_tr = tg_ha_tr.derivative()
        #con_tr = [(tg_ha_tr, tg_ha_tr0), (dtg_ha_tr, T * dtg_ha_tr0)]
        con_tr = [(tg_ha_tr, tg_ha_tr0)]
        con_veh = self.lead_veh.get_initial_constraints(splines[1:])
        return con_tr + con_veh  # put in one list

    def get_terminal_constraints(self, splines):
        # Only impose if self.theta_trT exists, e.g. if parking a trailer
        if hasattr(self, 'theta_trT'):
            tg_ha_tr = splines[0]
            tg_ha_trT = self.define_parameter('tg_ha_trT', 1)
            term_con_tr = [(tg_ha_tr, tg_ha_trT)]
            term_con_der_tr = []
        else:
            term_con_tr, term_con_der_tr = [], []
        con_veh = self.lead_veh.get_terminal_constraints(splines[1:])
        term_con_veh = con_veh[0]
        term_con_der_veh = con_veh[1]
        term_con = term_con_tr + term_con_veh
        term_con_der = term_con_der_tr + term_con_der_veh
        return [term_con, term_con_der]

    def set_initial_conditions(self, state, input=None):
        if input is None:
            input = np.zeros(3)
        theta = state
        # add complete state(6 elements) and input(2 elements)
        # [x_tr, y_tr, theta_tr, x_veh, y_veh, theta_veh]
        state = np.zeros(6)
        state[2] = theta  # theta, imposed on trailer by the user
        # Build up prediction of complete system.
        # Note that this requires initializing the vehicle before the trailer
        state[3:] = self.lead_veh.prediction['state']
        input = self.lead_veh.prediction['input']
        self.prediction['state'] = state
        self.prediction['input'] = input

    def set_terminal_conditions(self, theta):
        # Optional, e.g. only for parking a trailer
        self.theta_trT = np.radians(theta[0])

    def get_init_spline_value(self):
        init_value_tr = np.zeros((len(self.basis), 1))
        tg_ha_tr0 = np.tan(self.prediction['state'][2] / 2.)
        if hasattr(self, 'theta_trT'):
            tg_ha_trT = np.tan(self.theta_trT / 2.)
        else:
            tg_ha_trT = tg_ha_tr0
        init_value_tr[:, 0] = np.linspace(tg_ha_tr0, tg_ha_trT, len(self.basis))
        init_value_veh = self.lead_veh.get_init_spline_value()
        init_value = np.c_[init_value_tr, init_value_veh]
        return init_value

    def check_terminal_conditions(self):
        # Two options: move vehicle with a trailer, or position/park the trailer somewhere.
        # Move vehicle with trailer: no theta_trT specified
        # Park vehicle with trailer: theta_trT specified, True if vehicle and trailer pose reached.
        tol = self.options['stop_tol']
        if hasattr(self, 'theta_trT'):
            if (np.linalg.norm(self.signals['state'][2, -1] - self.theta_trT) > tol):  # is de hoek niet te groot?
                result = False
            else:
                result = True
        else:  # theta_trT reached or not specified
            result = True
        result = (self.lead_veh.check_terminal_conditions() and result)  # arrived if lead_veh and trailer checks both True
        return result

    def set_parameters(self, current_time):
        #verplaatst in vergelijking met oude toolbox
        pred_veh = {}
        pred_veh['input'] = self.prediction['input']
        pred_veh['state'] = self.prediction['state'][3:, ]
        self.lead_veh.update_prediction(pred_veh)
        ##############
        parameters = Vehicle.set_parameters(self, current_time)
        parameters_tr = {}
        parameters_tr['tg_ha_tr0'] = np.tan(self.prediction['state'][2] / 2.)
        #####



        parameters_tr['dtg_ha_tr0'] = 0.5 * (self.prediction['input'][0] / self.l_hitch1 * (
        np.sin(self.prediction['state'][5] - self.prediction['state'][2])) +(self.prediction['input'][1]/ self.l_hitch1-
                                             self.prediction['input'][2]*self.l_hitch / self.l_hitch1) * (
                                             np.cos(self.prediction['state'][5] - self.prediction['state'][2])))* (1 + parameters_tr['tg_ha_tr0'] ** 2)  # dtg_ha
        #####
        if hasattr(self, 'theta_trT'):
            parameters_tr['tg_ha_trT'] = np.tan(self.theta_trT / 2.)
        parameters_veh = self.lead_veh.set_parameters(current_time)
        parameters.update(parameters_tr)
        parameters.update(parameters_veh)
        return parameters

    def define_collision_constraints_trailer(self, hyperplanes_lead_veh, hyperplanes_trailer, environment, splines):
        tg_ha_tr, x_veh, y_veh, tg_ha_veh = splines


        self.define_collision_constraints_2d(hyperplanes_trailer, environment, [x_veh, y_veh], tg_ha_tr, -self.l_hitch1,tg_ha_veh, -self.l_hitch)
        #####
        self.lead_veh.define_collision_constraints(hyperplanes_lead_veh, environment, splines[1:])

    def splines2signals(self, splines, time):
        # als splines al uitgerekend zijn tot getallen
        signals = {}
        tg_ha_tr = splines[0]
        dtg_ha_tr = tg_ha_tr.derivative()
        tg_ha_tr = np.array(sample_splines([tg_ha_tr], time))
        dtg_ha_tr = np.array(sample_splines([dtg_ha_tr], time))
        theta_tr = 2 * np.arctan2(tg_ha_tr, 1)
        signals_veh = self.lead_veh.splines2signals(splines[1:], time)

        #####
        tg_ha_veh = splines[3]
        tg_ha_veh = np.array(sample_splines([tg_ha_veh], time))

        theta_veh = 2 * np.arctan2(tg_ha_veh, 1)
        x_tr = signals_veh['state'][0, :] - self.l_hitch * np.cos(theta_veh) - self.l_hitch1 * np.cos(theta_tr)
        y_tr = signals_veh['state'][1, :] - self.l_hitch * np.sin(theta_veh) - self.l_hitch1 * np.sin(theta_tr)
        #####


        # input_tr = np.c_[signals_veh['input'][0, :], signals_veh['state'][2, :]].T  # V_veh, theta_veh
        signals['state'] = np.r_[x_tr, y_tr, theta_tr, signals_veh['state']]  # trailer state
        signals['pose'] = signals['state']
        signals['input'] = signals_veh['input']
        signals['r1'] = np.r_[tg_ha_tr, dtg_ha_tr]
        return signals

    def ode(self, state, input):
        # state = [x_tr, y_tr, theta_tr, x_veh, y_veh, theta_veh]
        # input = [V_veh, dtheta_veh]
        # state: theta_tr
        # input: V_veh, theta_veh
        # ode: dtheta_tr = V_veh/l_hitch*sin(theta_veh-theta_tr)
        _, _, theta_tr, x_veh, y_veh, theta_veh = state

        #####
        v_x,v_y, dtheta_veh = input  # dtheta_veh zal nodig zijn om volgende stappen te kunnen berekenen.
        #alpha = theta_veh - theta_tr
        #dtheta_tr = 1/ self.l_hitch1 * (v_x*np.sin(alpha) +(v_y - dtheta_veh * self.l_hitch) * np.cos(alpha))
        dtheta_tr = 1/self.l_hitch1 *(-np.sin(theta_tr)*(v_x+self.l_hitch*np.sin(theta_veh)*dtheta_veh)+np.cos(theta_tr)*(v_y-self.l_hitch*np.cos(theta_veh)*dtheta_veh))
        ode_veh = self.lead_veh.ode([x_veh, y_veh, theta_veh],
                                    input)  # pass on state and input which are related to veh

        ode_trailer = np.r_[
            ode_veh[0] + self.l_hitch * np.sin(theta_veh) * dtheta_veh + self.l_hitch1 * np.sin(theta_tr) * dtheta_tr,
            ode_veh[1] - self.l_hitch * np.cos(theta_veh) * dtheta_veh - self.l_hitch1 * np.cos(theta_tr) * dtheta_tr,
            dtheta_tr].T
        #####
        ode = np.r_[ode_trailer, ode_veh]
        return ode

    def state2pose(self, state):
        pose_veh = self.lead_veh.state2pose(state[3:])
        pose_tr = state[:3]
        return np.r_[pose_tr, pose_veh]

    def draw(self, t=-1):
        ret = []
        for shape in self.shapes:
            ret += shape.draw(self.signals['pose'][:3, t])
            # plot connection between car and trailer
            if isinstance(shape, (Circle, Square)):
                dist = shape.radius
            elif isinstance(shape, (Rectangle)):
                dist = shape.width / 2.
            else:
                raise ValueError('Selected a shape different than Circle,\
                 Rectangle or Square, which is not implemented yet')
                # start on midpoint trailer, go to side

            #####
            pt1 = self.signals['pose'][:2, t] + dist * np.array([np.cos(self.signals['pose'][2, t]),
                                                                 np.sin(self.signals['pose'][2, t])])
            # start on midpoint trailer, go to side + l_hitch, but l_hitch was defined as distance between
            # midpoint of trailer and connection point on vehicle so this already contains 'dist' --> use l_hitch

            pt2 = self.signals['pose'][:2, t] + (self.l_hitch1) * np.array([np.cos(self.signals['pose'][2, t]),
                                                                            np.sin(self.signals['pose'][2, t])])
            # stuk tussen trailer middelpunt en hitchpoint
            ret += [np.array([pt1, pt2]).T]

            pt3 = pt2 + (self.l_hitch) * np.array([np.cos(self.signals['pose'][5, t]),
                                                   np.sin(self.signals['pose'][5, t])])
            # stuk tussen middelpunt voertuig en hitchpoint.
            ret += [np.array([pt2, pt3]).T]

        #####
        # signals and pred are required for drawing and some other functions of lead_veh
        # since this vehicle is not simulated separately it doesn't get a self.signals attribute and
        # its self.prediction is not updated
        signals_veh = {}
        signals_veh['pose'] = self.signals['pose'][3:, ]
        signals_veh['state'] = self.signals['state'][3:, ]
        signals_veh['input'] = self.signals['input']
        self.lead_veh.update_signals(signals_veh)
        ################ verplaatst in nieuwe toolbox
        # pred_veh = {}
        # pred_veh['input'] = self.prediction['input']
        # pred_veh['state'] = self.prediction['state'][3:, ]
        #self.lead_veh.update_prediction(pred_veh)
        #################################""""""""
        ret += self.lead_veh.draw(t)
        return ret
