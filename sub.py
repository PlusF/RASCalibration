import numpy as np
import pandas as pd


def main():
    raw = r'C:\Users\kaneda\Desktop\data\scan500.txt'
    with open(raw, 'r') as f:
        meta_data = f.readlines()[:7]
    df = pd.read_csv(raw, skiprows=4, header=None)
    filenames = [
        r'C:\Users\kaneda\Desktop\data\scan500c.txt',
        r'C:\Users\kaneda\Desktop\data\scan630c.txt',
        r'C:\Users\kaneda\Desktop\data\scan760c.txt',
    ]
    values = []
    for filename in filenames:
        df = pd.read_csv(filename, skiprows=11, header=None)
        values.append(df.values)

    data = np.vstack(values)

    with open(r'C:\Users\kaneda\Desktop\data\concat.txt', 'w') as f:
        for m in meta_data:
            f.write(m)
        for d in data:
            f.write(f'{",".join(d.astype(str))}\n')


if __name__ == '__main__':
    main()
