import math
import numpy as np

from constants import Const

class Interaction:

    def __init__(self, ngrid, nch, rgrid2):

        self.ngrid = ngrid
        self.nch = nch
        self.rgrid2 = rgrid2

    def get_perturbations(self, jrot, mass, par, 
        channels, couplings, fgrid, dd, Gy2):

        self.fgrid = fgrid
        self.jrot = jrot

        self.pert_matrix = np.zeros((self.nch*self.ngrid)**2).reshape(
            self.nch*self.ngrid, self.nch*self.ngrid
        )

        for cp in range(0, len(couplings)):

            if isinstance(couplings[cp].interact[0], tuple):
                props = zip(
                    couplings[cp].interact, 
                    couplings[cp].coupling, 
                    couplings[cp].multiplier
                )
                
                for inter, ctype, m in props:

                    ch1, ch2 = inter[0:2]
                    cb = (ch1, ch2)
                    
                    args = self.get_quantum_numbers(channels, ch1, ch2)

                    self.fill_pert_matrix(Gy2, ctype=ctype, m=m, cp=cp, cb=cb, 
                        mass=mass, par=par, dd=dd, args=args
                    )
            else:
                ctype = couplings[cp].coupling
                m = couplings[cp].multiplier

                ch1, ch2 = couplings[cp].interact[0:2]
                cb = (ch1, ch2)

                args = self.get_quantum_numbers(channels, ch1, ch2)

                self.fill_pert_matrix(Gy2, ctype=ctype, m=m, cp=cp, cb=cb,
                    mass=mass, par=par, dd=dd, args=args
                )
            
        return self.pert_matrix

    def get_quantum_numbers(self, channels, ch1, ch2):

        return {
            'lm1': channels[ch1-1].nlambda,
            'sg1': channels[ch1-1].nsigma,
            'om1': channels[ch1-1].omega,
            'lm2': channels[ch2-1].nlambda,
            'sg2': channels[ch2-1].nsigma,
            'om2': channels[ch2-1].omega,
            's1': (channels[ch1-1].mult-1)/2,
            's2': (channels[ch2-1].mult-1)/2
        }

    def define_interaction_keys(self):

        return {
            'spin-orbit': self.spin_orbit_interaction,
            'lj': self.lj_interaction,
            'lj_parity': self.lj_parity_interaction,
            'sj': self.sj_interaction,
            'sj_parity': self.sj_parity_interaction,
            'sl': self.spin_electornic_interaction,
            'lambdadf': self.lambda_doubling_f_parity,
            'lambdade': self.lambda_doubling_e_parity,
            'lambdad': self.lambda_doubling,
            'bobc': self.BOBC,
            'dbobc': self.DBOBC,
            'spin-rot': self.spin_rotation_interaction,
            'spin-spin': self.spin_spin_interaction,
        }

    def fill_pert_matrix(self, Gy2, **kwargs):

        ctype = kwargs['ctype'].lower()
        m = kwargs['m']
        cp = kwargs['cp']
        cb = kwargs['cb']
        mass = kwargs['mass']
        par = kwargs['par']
        dd = kwargs['dd']
        args = kwargs['args']

        interaction_keys = self.define_interaction_keys()

        cplfunc = np.zeros(self.ngrid)

        jjrot = self.jrot*(self.jrot + 1.0)
        ch1, ch2 = cb

        i1 = cp*self.ngrid
        i2 = (cp+1)*self.ngrid

        ycs = self.fgrid[i1:i2]

        cplfunc = interaction_keys[ctype](jjrot, mass, m, par, ycs, args) * Gy2

        row1 = (ch1-1)*self.ngrid
        row2 = ch1*self.ngrid
        col1 = (ch2-1)*self.ngrid
        col2 = ch2*self.ngrid

        self.pert_matrix[row1:row2, col1:col2][dd] += cplfunc

    def spin_orbit_interaction(self, jjrot, mass, m, par, ycs, args):

        """
        Calculate diagonal and off-diagonal Spin-Orbit coupling matrix element
        <State1| SO |State1> = multiplier * A(R)
        <State1| SO |State2> = multiplier * alpha(R)

        with selection rules:

        """

        socoef = m * (self.rule_SOdiag(args) or self.rule_SOnondiag(args))
        
        return (ycs / Const.hartree) * socoef
    
    def rule_SOdiag(self, args):

        if args['lm1'] == args['lm2'] and \
            args['sg1'] == args['sg2'] and \
            args['om1'] == args['om2']:
            return 1

        return 0

    def rule_SOnondiag(self, args):

        if args['lm1'] != args['lm2'] or \
            args['sg1'] != args['sg2'] or \
            args['om1'] != args['om2']:
            return 1

        return 0

    def lj_interaction(self, jjrot, mass, m, par, ycs, args):
        """
        Calculate the matrix element of L-uncoupling operator
        <State1| LJ |State1> = 
        <State1| LJ |State2> = 

        with selection rules:
            
        """

        qexpression = 1.0

        rule_omegaj = self.rule_lj_interaction(args) and \
            math.sqrt(jjrot - (args['om1'] * args['om2']))

        ljcoef = m * qexpression * rule_omegaj

        brot = 1.0 / (2.0 * mass * self.rgrid2)

        sign = -1.0

        return sign * ycs * brot * ljcoef
    
    def rule_lj_interaction(self, args):
        
        # to check the abs values
        rule_lj = (abs(args['om1'] - args['om2']) == (abs(args['lm1'] - args['lm2'])) == 1.0) or \
            (abs(args['om1'] - args['om2']) == (abs(args['lm1'] - args['lm2']) == -1.0))

        # rule_lj = ((args['om1'] - args['om2']) == (args['lm1'] - args['lm2']) == 1.0) or \
        #    ((args['om1'] - args['om2']) == (args['lm1'] - args['lm2']) == -1.0)
        #print('LJ', rule_lj)

        # # to check!!!
        sg1 = args['sg1']
        if args['om1'] == 0 and args['sg1'] < 0:
            sg1 = abs(args['sg1'])

        sg2 = args['sg2']        
        if args['om2'] == 0 and args['sg2'] < 0:
            sg2 = abs(args['sg2'])

        #if args['sg1'] == args['sg2'] and args['s1'] == args['s2'] and rule_lj and \
        if sg1 == sg2 and args['s1'] == args['s2'] and rule_lj and \
            (args['om1'] <= self.jrot and args['om2'] <= self.jrot+1.0):
            return 1

        return 0

    def lj_parity_interaction(self, jjrot, mass, m, par, ycs, args):

        qexpression = math.sqrt(jjrot + args['om1'] * args['om2'])

        ljcoef = m * qexpression * self.rule_lj_parity(args)

        brot = 1.0 / (2.0 * mass * self.rgrid2)

        sign = 1.0 # f-parity
        if par == 1:
            sign = -1.0 # e-parity

        return sign * ycs * brot * ljcoef

    def rule_lj_parity(self, args):
        '''
        This interaction is allowed only between Sigma-Pi or Sigma-Sigma states
        with even multiplicity with Lambda <= 1 and abs(Omega) = 0.5
        '''

        rule_even_mult = (2 * args['sg1'] + 1) % 2 == 0 and \
            (2 * args['sg2'] + 1) % 2 == 0

        if 0 <= args['lm1'] <= 1 and 0 <= args['lm2'] <= 1 and \
            (not args['lm1'] == args['lm2'] == 1) and rule_even_mult and \
            args['om1'] == args['om2'] == 0.5:
            return 1

        return 0

    def sj_interaction(self, jjrot, mass, m, par, ycs, args):
        """
        Calculate the matrix element of S-uncoupling operator
        <State1| SJ |State1> = 
        <State1| SJ |State2> = 

        with selection rules:
            
        """

        qexpression = math.sqrt(jjrot - (args['om1'] * args['om2'])) * \
            math.sqrt(args['s1']  * (args['s1'] + 1) - args['sg1'] * args['sg2'])

        rule_omegaj = self.rule_sj_interaction(args) 

        sjcoef = m * qexpression * rule_omegaj

        brot = 1.0 / (2.0 * mass * self.rgrid2)

        sign = -1.0

        return sign * ycs * brot * sjcoef

    def rule_sj_interaction(self, args):

        rule_sj = ((args['om1'] - args['om2']) == (args['sg1'] - args['sg2']) == 1.0) or \
            ((args['om1'] - args['om2']) == (args['sg1'] - args['sg2']) == -1.0)

        if args['lm1'] == args['lm2'] and args['s1'] == args['s2'] and rule_sj and \
            (args['om1'] <= self.jrot and args['om2'] <= self.jrot+1.0):
            return 1

        return 0

    def sj_parity_interaction(self, jjrot, mass, m, par, ycs, args):
        '''
            only between Sigma states
        '''

        qexpression = math.sqrt(jjrot + args['om1'] * args['om2'])

        sjcoef = m * qexpression * self.rule_sj_parity(args)

        brot = 1.0 / (2.0 * mass * self.rgrid2)

        sign = 1.0 # f-parity
        if par == 1:
            sign = -1.0 # e-parity

        return sign * ycs * brot * sjcoef

    def rule_sj_parity(self, args):

        if args['lm1'] == args['lm2'] == 0 and args['s1'] == args['s2']:
            return 1

        return 0

    def spin_electornic_interaction(self, jjrot, mass, m, par, ycs, args):
        """
        Calculate the matrix element of spin-electronic operator
        <State1| LS |State1> = 
        <State1| LS |State2> = 

        with selection rules:
            
        """

        qexpression = math.sqrt((args['s1'] * (args['s1'] + 1)) - args['sg1'] * args['sg2'])

        slcoef = m * qexpression * self.rule_spin_electronic(args)

        brot = 1.0 / (2.0 * mass * self.rgrid2)

        sign = 1.0

        return sign * ycs * brot * slcoef

    def rule_spin_electronic(self, args):

        rule_ls = ((args['lm1'] - args['lm2']) == (args['sg2'] - args['sg1']) == 1.0) or \
            ((args['lm1'] - args['lm2']) == (args['sg2'] - args['sg1']) == -1.0)

        if args['om1'] == args['om2'] and args['s1'] == args['s2'] and rule_ls:
            return 1

        return 0

    def lambda_doubling(self, jjrot, mass, m, par, ycs, args):

        ldcoef = jjrot / (2.0 * mass * self.rgrid2)**2

        return ycs * m * ldcoef * Const.hartree

    def lambda_doubling_e_parity(self, jjrot, mass, m, par, ycs, args):

        if par == 1:
            self.lambda_doubling(jjrot, mass, m, par, ycs, args)

    def lambda_doubling_f_parity(self, jjrot, mass, m, par, ycs, args):

        if par == 0:
            self.lambda_doubling(jjrot, mass, m, par, ycs, args)

    def BOBC(self, jjrot, mass, m, par, ycs, args):

        bocoef = jjrot / (2.0 * mass * self.rgrid2)

        return ycs * m * bocoef * Const.hartree

    def DBOBC(self, jjrot, mass, m, par, ycs, args):

        return (ycs / Const.hartree) * m

    def spin_rotation_interaction(self, jjrot, mass, m, par, ycs, args):

        if self.rule_spin_rot_diag(args):

            qexpression = args['sg1']**2 - args['s1']*(args['s2'] + 1.0)

        elif self.rule_spin_rot_nondiag(args):
            qexpression = math.sqrt(jjrot - (args['om1'] * args['om2'])) * \
                math.sqrt(args['s1']  * (args['s1'] + 1) - args['sg1'] * args['sg2'])

        srcoef = m * qexpression

        sign = 1.0

        return sign * ycs * srcoef

    def rule_spin_rot_diag(self, args):

        if args['om1'] == args['om2'] and \
            args['s1'] == args['s2'] and \
            args['sg1'] == args['sg2'] and \
            args['lm1'] == args['lm2']:
            return 1

        return 0

    def rule_spin_rot_nondiag(self, args):

        self.rule_sj_interaction(args)

    def spin_spin_interaction(self, jjrot, mass, m, par, ycs, args):

        if self.rule_spin_spin_diag(args):
            qexpression = 3 * args['sg1']**2 - args['s1']*(args['s2'] + 1.0)
        
        elif self.rule_spin_spin_nondiag(args):
            qexpression = 1.0

        sscoef = m * qexpression

        sign = 1.0

        return sign * ycs * sscoef

    def rule_spin_spin_nondiag(self, args):

        # Delta Sigma = +/- 1
        rule_ss1_1so = ((args['lm1'] - args['lm2']) == -1.0 * (args['sg2'] - args['sg1']) == 1.0) or \
            ((args['lm1'] - args['lm2']) == -1.0 * (args['sg1'] - args['sg2']) == -1.0) 
        
        # Delta Sigma = +/- 2
        rule_ss2_2so = ((args['lm1'] - args['lm2']) == -1.0 * (args['sg2'] - args['sg1']) == 2.0) or \
            ((args['lm1'] - args['lm2']) == -1.0 * (args['sg1'] - args['sg2']) == -2.0)

        rule_ss1 = (args['s1'] - args['s2']) == 1.0 or \
            (args['s1'] - args['s2']) == -1.0 and \
            rule_ss1_1so

        rule_ss2 = (args['s1'] - args['s2']) == 2.0 or \
            (args['s1'] - args['s2']) == -2.0 and \
            rule_ss2_2so

        if rule_ss1 or rule_ss2:
            return 1

        return 0

    def rule_spin_spin_diag(self, args):

        if args['om1'] == args['om2'] and \
            args['s1'] == args['s2'] and \
            args['sg1'] == args['sg2']:
            return 1

        return 0
