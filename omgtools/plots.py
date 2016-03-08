import os
import matplotlib
matplotlib.use('TKAgg')
import matplotlib.pyplot as plt
import numpy as np

# color definition (rgb)
blue = [17., 110., 138.]
red = [138.,  31.,  17.]
green = [17., 138.,  19.]
lightblue = [106., 194., 238.]


def mix_with_white(color, perc_white=80.):
    r, g, b = color[0], color[1], color[2]
    r_m = ((100. - perc_white)*r + perc_white)/100.
    g_m = ((100. - perc_white)*g + perc_white)/100.
    b_m = ((100. - perc_white)*b + perc_white)/100.
    return [r_m, g_m, b_m]


class Plots:

    def __init__(self, fleet, environment, options={}):
        self.fleet = fleet
        self.vehicles = fleet.vehicles
        self.environment = environment

        self.other_plt = {}
        self.plots = []

        # default colors
        self.set_color_template([blue, red, green, lightblue])

        self.set_options(options)
        plt.ion()
        plt.show()

    def set_color_template(self, colors):
        colors = [[c/255. for c in color] for color in colors]
        ind = 0
        while self.fleet.N > len(colors):
            colors.append(colors[ind])
            ind += 1
        self.clr = {veh: colors[l] for l, veh in enumerate(self.vehicles)}
        self.clr_w = {veh: mix_with_white(c) for veh, c in self.clr.items()}

    # ========================================================================
    # Plot options
    # ========================================================================

    def set_options(self, options):
        if 'knots' in options and options['knots']:
            knots = {'symbol': 'x'}
            knots['time'] = lambda veh, t: veh.trajectories_kn['time'][t]
            knots['data'] = lambda veh, signal, k, t: veh.trajectories_kn[
                signal][t][k, :, :]
            self.other_plt['knots'] = knots
        if 'prediction' in options and options['prediction']:
            prediction = {'symbol': 'o'}
            prediction['time'] = lambda veh, t: veh.path['time'][t]
            prediction['data'] = lambda veh, signal, k, t: veh.predictions[
                signal][t][k]
            self.other_plt['prediction'] = prediction

    # ========================================================================
    # Plot creation and initialization
    # ========================================================================

    def create(self, signal, **kwargs):
        if 'vehicles' in kwargs:
            vehicles = kwargs['vehicles']
        else:
            vehicles = self.vehicles
        if signal in ('2d', '2D'):
            plots = self._init_2d_plot(vehicles)
            self.plots.append(plots)
        else:
            vehicle_types = self._sort_vehicles(vehicles)
            plots = []
            for vehicle_type, vehicles in vehicle_types.items():
                plot = self._init_curve_plot(signal, vehicles, **kwargs)
                self.plots.append(plot)
                plots.append(plot)
        return plots

    def _init_curve_plot(self, signal, vehicles, **kwargs):
        plt_traj, plt_path, plt_other = [], [], {}
        for key in self.other_plt.keys():
            plt_other[key] = []
        sgn_length = vehicles[0].signal_length[signal]
        if 'label' in kwargs:
            label = kwargs['label']
            if not isinstance(label, list):
                label = [label]
        else:
            if sgn_length > 1:
                label = [signal+str(k) for k in range(sgn_length)]
            else:
                label = [signal]
        figure, axis = plt.subplots(sgn_length, 1, squeeze=False)
        for k in range(sgn_length):
            axis[k, 0].set_xlabel('t (s)')
            axis[k, 0].set_ylabel(label[k])
        plt_traj = [[axis[k, 0].plot([], [], '-', color=self.clr_w[veh])[0]
                     for k in range(sgn_length)] for veh in vehicles]
        plt_path = [[axis[k, 0].plot([], [], '-', color=self.clr[veh])[0]
                     for k in range(sgn_length)] for veh in vehicles]
        for key, other in self.other_plt.items():
            plt_other[key] = [[axis[k, 0].plot([], [], other['symbol'],
                                               color=self.clr[veh])[0]
                               for k in range(veh.signal_length[signal])]
                              for veh in vehicles]
        return {'type': 'curve', 'figure': figure, 'axis': axis,
                'trajectory': plt_traj, 'path': plt_path,
                'other': plt_other, 'signal': signal, 'vehicles': vehicles}

    def _init_2d_plot(self, vehicles):
        figure = plt.figure()
        axis = figure.add_subplot(111)
        canvas_lim = self.environment.get_canvas_limits()
        plt.xlim(canvas_lim[0][0], canvas_lim[0][1])
        plt.ylim(canvas_lim[1][0], canvas_lim[1][1])
        plt_2d = {}
        plt_2d['environment'] = [
            axis.plot([], [], 'k-')[0] for l in range(self.environment.No)]
        plt_2d['trajectory'] = [axis.plot(
            [], [], '-', color=self.clr_w[veh])[0] for veh in vehicles]
        plt_2d['path'] = [axis.plot(
            [], [], '-', color=self.clr[veh])[0] for veh in vehicles]
        plt_2d['vehicle'] = [axis.plot(
            [], [], '-', color=self.clr[veh])[0] for veh in vehicles]
        return {'type': '2d', 'figure': figure, 'axis': axis,
                '2d': plt_2d, 'vehicles': vehicles}

    def _sort_vehicles(self, vehicles):
        vehicle_types = {}
        for vehicle in vehicles:
            veh_type = vehicle.__class__.__name__
            if veh_type in vehicle_types:
                vehicle_types[veh_type].append(vehicle)
            else:
                vehicle_types[veh_type] = [vehicle]
        return vehicle_types

    # ========================================================================
    # Plot update
    # ========================================================================

    def update(self, t=-1, plots=None):
        plots = self.plots if (plots is None) else plots
        plots = plots if isinstance(plots, list) else [plots]
        for plot in plots:
            if plot['type'] == 'curve':
                self._update_curve_plot(plot, t)
            if plot['type'] == '2d':
                self._update_2d_plot(plot, t)

    def _update_curve_plot(self, plot, t=-1):
        plt_traj = plot['trajectory']
        plt_path = plot['path']
        plt_other = plot['other']
        signal, vehicles = plot['signal'], plot['vehicles']
        for l, veh in enumerate(vehicles):
            for k in range(veh.signal_length[signal]):
                plt_traj[l][k].set_data(
                    veh.trajectories['time'][t].ravel(),
                    veh.trajectories[signal][t][k, :, :].ravel())
                if t == -1:
                    plt_path[l][k].set_data(
                        veh.path['time'].ravel(),
                        veh.path[signal][k, :, :].ravel())
                else:
                    plt_path[l][k].set_data(
                        veh.path['time'][:t+1].ravel(),
                        veh.path[signal][k, :, :t+1].ravel())
                for key, other in self.other_plt.items():
                    plt_other[key][l][k].set_data(
                        other['time'](veh, t).ravel(),
                        other['data'](veh, signal, k, t).ravel())
        fig, ax = plot['figure'], plot['axis']
        for i in range(ax.shape[0]):
            for j in range(ax.shape[1]):
                ax[i, j].relim()
                ax[i, j].autoscale_view(True, True, True)
        fig.canvas.draw()

    def _update_2d_plot(self, plot, t=-1):
        plt_2d, vehicles = plot['2d'], plot['vehicles']
        environment = self.environment.draw(t)
        for l, env in enumerate(environment):
            plt_2d['environment'][l].set_data(
                env[0, :].ravel(), env[1, :].ravel())
        for l, veh in enumerate(vehicles):
            if t == -1:
                pos_path = veh.path['position'][:, :]
            else:
                pos_path = veh.path['position'][:, :, :t+1]
            pos_traj = veh.trajectories['position'][t]
            veh_cnt = veh.draw(t)
            plt_2d['trajectory'][l].set_data(pos_traj[0, :].ravel(),
                                             pos_traj[1, :].ravel())
            plt_2d['path'][l].set_data(pos_path[0, :].ravel(),
                                       pos_path[1, :].ravel())
            plt_2d['vehicle'][l].set_data(veh_cnt[0].ravel(),
                                          veh_cnt[1].ravel())
        plot['figure'].canvas.draw()

    # ========================================================================
    # Post processing operations
    # ========================================================================

    def _time2index(self, vehicle, time):
        time_axis = vehicle.path['time']
        Ts = time_axis[1] - time_axis[0]
        for k, t in enumerate(time_axis):
            t = np.round(t, 6)
            if (t <= time) and (time < (t+Ts)) and ((time-t) <= (t+Ts-time)):
                return k

    def show(self, signal, **kwargs):
        if 'time' in kwargs:
            index = self._time2index(self.vehicles[0], kwargs['time'])
        elif 'index' in kwargs:
            index = kwargs['index']
        else:
            index = -1
        plot = self.create(signal, **kwargs)
        self.update(t=index, plots=plot)

    def save(self, signal, name='plot', path='images/', **kwargs):
        from matplotlib2tikz import save as tikz_save
        directory = path
        if not os.path.isdir(directory):
            os.makedirs(directory)
        self.show(signal, **kwargs)
        figurewidth = kwargs[
            'figurewidth'] if 'figurewidth' in kwargs else '8cm'
        tikz_save(directory+'/'+name+'.tikz', figurewidth=figurewidth)

    def show_movie(self, signal, repeat=False, **kwargs):
        t = self.vehicles[0].path['time']
        if ('number_of_frames' in kwargs and
                kwargs['number_of_frames'] <= (len(t)-1)):
            number_of_frames = kwargs['number_of_frames']
        else:
            number_of_frames = len(t)-1
        subsample = (len(t)-1)/(number_of_frames-1)
        plot = self.create(signal, **kwargs)
        while True:
            for k in range(0, len(t)-1, subsample):
                self.update(k, plots=plot)
            if not repeat:
                break

    def save_movie(self, signal, name='movie', path='movies/', **kwargs):
        from matplotlib2tikz import save as tikz_save
        directory = path + name
        if not os.path.isdir(directory):
            os.makedirs(directory)
        t = self.vehicles[0].path['time']
        if ('number_of_frames' in kwargs and
                kwargs['number_of_frames'] <= (len(t)-1)):
            number_of_frames = kwargs['number_of_frames']
        else:
            number_of_frames = len(t)-1
        figwidth = kwargs['figurewidth'] if 'figurewidth' in kwargs else '8cm'
        subsample = (len(t)-1)/(number_of_frames-1)
        plot = self.create(signal, **kwargs)
        cnt = 0
        if signal in ('2d', '2D'):
            plt.axis('off')
        for k in range(0, len(t)-1, subsample):
            self.update(k, plots=plot)
            tikz_save(
                directory+'/'+name+'_'+str(cnt)+'.tikz', figurewidth=figwidth)
            cnt += 1