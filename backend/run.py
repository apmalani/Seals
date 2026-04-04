import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conf
import pandas as pd

def main():
    t0 = time.time()
    os.makedirs(conf.DATA_DIR, exist_ok=True)
    os.makedirs(conf.MODELS_DIR, exist_ok=True)
    os.makedirs(conf.RESULTS_DIR, exist_ok=True)

    if os.path.exists(conf.COMBINED_CSV):
        df = pd.read_csv(conf.COMBINED_CSV, parse_dates=["eventDate"])
        df["eventDate"] = pd.to_datetime(df["eventDate"], utc=True)
        print("loaded %d rows from cache (%d pos)" % (len(df), (df["target"]==1).sum()))
    else:
        from src.get_obs import build_it
        df = build_it()

    from src.env_data import run_backfill
    df = run_backfill(df)

    from src.feat_eng import add_feats
    df = add_feats(df)

    df.to_csv(conf.FINAL_CSV, index=False)
    print("saved %d rows x %d cols -> %s" % (len(df), len(df.columns), conf.FINAL_CSV))

    from src.train import do_train, train_species, dump_results, make_plots
    s1 = do_train(df)
    s2 = train_species(df)
    dump_results(df, s1, s2)
    make_plots(s1, s2)

    print("\ndone in %ds" % int(time.time() - t0))

if __name__ == "__main__":
    main()
