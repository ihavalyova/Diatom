import numpy as np

from constants import Const


class Grid:

    def __init__(self, npoints, rgrid, solver='sinc', alpha=0.0, rbar=0.0):

        self.ngrid = npoints
        self.rmin = rgrid[0] / Const.bohr
        self.rmax = rgrid[1] / Const.bohr
        rbar = rbar / Const.bohr
        self.solver = solver.lower()

        self.Gy = np.ones(self.ngrid)
        self.Fy = np.zeros(self.ngrid)
        self.rgrid = self.generate_uniform_grid()

        if alpha > 0.0:
            # mapping is allowed with sinc method only
            self.solver = 'sinc'

            self.rmin = self.get_grid_bounding_values(self.rmin, rbar, alpha)
            self.rmax = self.get_grid_bounding_values(self.rmax, rbar, alpha)

            self.rgrid, ygrid = self.generate_nonuniform_grid(alpha, rbar)

            gy_power1 = np.power(1.0+ygrid, (1.0/alpha)-1.0)
            gy_power2 = np.power(1.0-ygrid, (1.0/alpha)+1.0)
            self.Gy = (2.0*rbar/alpha) * gy_power1 / gy_power2

            fy_power = (np.power((1.0 - np.power(ygrid, 2)), 2))
            self.Fy = (1.0 - (1.0/(alpha**2))) / fy_power

    def get_grid_bounding_values(self, rlimit, rbar, alpha):

        return ((rlimit/rbar)**alpha - 1.0) / ((rlimit/rbar)**alpha + 1.0)

    def generate_uniform_grid(self):

        # FGH Fourier grid
        if self.solver == 'fourier':
            return np.linspace(self.rmin, self.rmax, num=self.ngrid,
                               endpoint=False)

        # FGH Sinc grid and FD5 grid
        return np.linspace(self.rmin, self.rmax, num=self.ngrid, endpoint=True)

    def generate_nonuniform_grid(self, alpha, rbar):

        ystep = (self.rmax - self.rmin) / (self.ngrid - 1)  # / ngrid - 1 ??
        # ygrid = np.ogrid[self.rmin+ystep:self.rmax+ystep:ystep]
        # ygrid = np.ogrid[self.rmin:self.rmax:ystep]
        # ygrid = np.linspace(self.rmin, self.rmax, num=self.ngrid)
        # ygrid = np.arange(self.rmin, self.rmax, step=ystep)
        # ygrid = np.linspace(
        # self.rmin, self.rmax, num=self.ngrid, endpoint=True
        # )

        ygrid = np.empty(self.ngrid)

        for j in range(1, self.ngrid+1):
            ygrid[j-1] = self.rmin + ystep*(j-1.0)

        Ry = rbar * np.power((1.0+ygrid) / (1.0-ygrid), 1.0/alpha)

        print(ygrid)
        print(len(ygrid))

        return Ry, ygrid


class CSpline:

    """Natural cubic spline interpolation algorithm
    """

    def __init__(self, x, y):

        self.x = x
        self.y = y

        self.Lmatrix = self.generate_spline()

    def cspline_check(self):

        try:
            self.check_input()
        except ValueError as ve:
            print(ve)

    def check_input(self):

        if not np.all(np.isfinite(self.x)):
            raise ValueError("`x` must be finite array.")
        if not np.all(np.isfinite(self.y)):
            raise ValueError("`y` must be finite array.")

        dx = np.diff(self.x)
        if np.any(dx <= 0):
            raise ValueError("`x` must be an increasing sequence.")

        if self.x.ndim != 1:
            raise ValueError("`x` must be 1-dimensional.")
        if self.x.shape[0] < 2:
            raise ValueError("`x` must contain at least 2 elements.")
        if self.x.shape[0] != self.y.shape[0]:
            raise ValueError(
                "The length of `y` doesn't match the length of `x`"
            )

    def generate_spline(self):

        # xgrid = np.linspace(x[0], x[-1], xgrid.shape[0], endpoint=False)

        n = self.x.shape[0]

        D = self.calculate_D_matrix(n)
        G = self.calculate_G_matrix(n)

        L = np.matmul(np.linalg.inv(D), G).transpose()
        L = np.c_[np.zeros(L.shape[0]), L, np.zeros(L.shape[0])]

        return L

    def calculate_D_matrix(self, n):

        # the lower diagonal, k=-1; (x_i - x_i-1)/6
        diag1 = (self.x[1:n-1] - self.x[0:n-2]) / 6.0

        # the diagonal, k=0;  (x_i+1 - x_i-1)/3
        diag0 = (self.x[2:n] - self.x[0:n-2]) / 3.0

        # the upper diagonal, k=1;  (x_i+1 - x_i)/6
        diag2 = (self.x[2:n] - self.x[1:n-1]) / 6.0

        return self.form_tridiag_matrix(diag1[1:], diag0, diag2[:-1])

    def calculate_G_matrix(self, n):

        # the diagonal, k=0; 1/(x_i - x_i-1)
        diag0 = 1.0 / (self.x[1:n-1] - self.x[0:n-2])

        # the upper diagonal, k=1; -1/(x_i+1 - x_i)-1/(x_i - x_i-1)
        diag1 = -1.0 / (self.x[2:n] - self.x[1:n-1]) - \
            (1.0 / (self.x[1:n-1] - self.x[0:n-2]))

        # above the upper diagonal, k=2; 1/(x_i+1 - x_i)
        diag2 = 1.0 / (self.x[2:n] - self.x[1:n-1])

        gmatrix = self.form_tridiag_matrix(
            diag0, diag1[:-1], diag2[:-2], k1=0, k2=1, k3=2
        )

        # include the last elements from the two upper diagonals
        col1 = np.zeros(gmatrix.shape[0])
        col1[-2:] = diag2[-2], diag1[-1]
        col2 = np.zeros(gmatrix.shape[0])
        col2[-1] = diag2[-1]

        # gmatrix will have size [(n-2) x n]
        gmatrix = np.c_[gmatrix, col1, col2]

        return gmatrix[:n-2, :]

    def form_tridiag_matrix(self, u, v, w, k1=-1, k2=0, k3=1):

        return np.diag(u, k1) + np.diag(v, k2) + np.diag(w, k3)

    def __call__(self, xgrid, return_deriv=False):

        n = self.x.shape[0]

        Sk = self.calculate_Sk_functions(n, xgrid, self.Lmatrix)

        ygrid = Sk.dot(self.y)

        if return_deriv:
            return ygrid, Sk

        return ygrid

    def calculate_coeff_A(self, xgrid, xi, xi1):

        return (xi1 - xgrid) / (xi1 - xi)

    def calculate_coeff_B(self, xgrid, xi, xi1):

        return (xgrid - xi) / (xi1 - xi)

    def calculate_coeff_C(self, xgrid, xi, xi1):

        ai = self.calculate_coeff_A(xgrid, xi, xi1)

        return (ai ** 3 - ai) * ((xi - xi1) ** 2) * (1.0 / 6.0)

    def calculate_coeff_D(self, xgrid, xi, xi1):

        bi = self.calculate_coeff_B(xgrid, xi, xi1)

        return (bi ** 3 - bi) * ((xi - xi1) ** 2) * (1.0 / 6.0)

    def calculate_Sk_functions(self, n, xgrid, L):

        # find the indices of the intervals for each interpolation point
        inds = np.searchsorted(self.x, xgrid, side='left')

        # the indices for the limiting cases
        inds = np.where(inds != 0, inds, 1)
        inds = np.where(inds < n, inds, n-1)
        x_in = 1*(xgrid >= self.x[0]) | 1*(xgrid <= self.x[n-1])

        Sk = np.zeros((xgrid.shape[0], n))

        a = self.calculate_coeff_A(xgrid, self.x[inds], self.x[inds-1])
        b = self.calculate_coeff_B(xgrid, self.x[inds], self.x[inds-1])
        c = self.calculate_coeff_C(xgrid, self.x[inds], self.x[inds-1])
        d = self.calculate_coeff_D(xgrid, self.x[inds], self.x[inds-1])

        for i in range(0, n):
            acoef = a * (1*(i == inds))
            bcoef = b * (1*(i == inds-1))
            ccoef = c * L[i, inds] * x_in
            dcoef = d * L[i, inds-1] * x_in

            Sk[:, i] = acoef + bcoef + ccoef + dcoef

        return Sk
