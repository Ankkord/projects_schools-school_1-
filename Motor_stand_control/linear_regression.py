import numpy as np

def linear_regression(points):
    """
    Аппроксимация прямой методом наименьших квадратов.

    :param points: список точек (x, y), где x и y - числа
    :return: кортеж (k, b, r_squared), где
             k, b - коэффициенты уравнения y = k*x + b,
             r_squared - коэффициент детерминации R^2
    """
    x = np.array([p[0] for p in points])
    y = np.array([p[1] for p in points])

    # Вычисляем коэффициенты k и b
    n = len(points)
    x_mean = np.mean(x)
    y_mean = np.mean(y)

    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    k = numerator / denominator
    b = y_mean - k * x_mean

    # Вычисляем R^2
    y_pred = k * x + b
    ss_total = np.sum((y - y_mean) ** 2)
    ss_residual = np.sum((y - y_pred) ** 2)
    r_squared = 1 - (ss_residual / ss_total)

    return k, b, r_squared