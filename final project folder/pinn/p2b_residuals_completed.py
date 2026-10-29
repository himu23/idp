#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE 2, PART B - THE PHYSICS RESIDUALS  ** THE CORE EXERCISE **
================================================================

This is the heart of the whole method and the one piece of code you must write
yourself. Everything else in a PINN is standard deep learning; the residual is
where the Saint-Venant equations enter.

Your task
---------
Implement `student_mass_residual` and `student_momentum_residual` below, from
the equations in the paper (Section 2). You are GIVEN the derivatives - u, h,
u_t, u_x, h_t, h_x are computed for you by automatic differentiation through
the trained network. You only have to assemble them into the residual.

The script then compares your residual against the engine's, point by point.
If your implementation is right, the difference is zero to machine precision.

Run
---
    python phase2_loss_analysis/p2b_residuals.py --case 3

Do NOT open engine/SVE_module_dynamic_h.py until you have made this pass. The
answer is sitting in `fun_r_mass` and `fun_r_momentum` and reading it first
wastes the exercise.

Author: Siddik Barbhuiya
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.environ.get('PINN_ROOT', os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import cases, dataprep, modelbuild  # noqa: E402

GRAVITY = 9.81


# ===========================================================================
#  YOUR CODE GOES HERE
# ===========================================================================

def student_mass_residual(u, h, u_t, u_x, h_t, h_x, cfg):
    """Continuity residual. Should be zero when mass is conserved.

    TODO: return the continuity residual used by this study.

    Careful. The textbook conservative form for a rectangular channel is

        dh/dt + d(u h)/dx  =  dh/dt + u dh/dx + h du/dx  =  0

    Look at what the engine actually implements before you assume. One of the
    three terms above is missing from the released code.

    In your report you must:
      (a) state which form the authors used,
      (b) state the assumption under which the two forms agree,
      (c) evaluate the neglected term on your case's reference field and say
          whether that assumption holds. Use the numbers, not a hand-wave.
    """
    # (a) The engine uses the NON-conservative, advective form  dh/dt + u dh/dx = 0.
    #     The full form for a rectangular channel is  dh/dt + u dh/dx + h du/dx = 0.
    # (b) The two agree only when h du/dx is negligible, i.e. velocity is (almost)
    #     uniform along the reach (du/dx ~ 0). The size of the dropped term is
    #     printed by quantify_dropped_term() below on the reference field.
    return h_t + u * h_x


def student_momentum_residual(u, h, u_t, u_x, h_t, h_x, cfg):
    """Momentum residual.

    TODO: return the dynamic-wave momentum residual:

        du/dt + u du/dx + g dh/dx + g (S_f - S_0)  =  0

    where S_0 is the bed slope (cfg / passed in as `slope`) and S_f is the
    friction slope from Manning's equation:

        S_f  =  n^2 |u| u / R^(4/3)

    with hydraulic radius R = b h / (2 h + b) for a rectangular channel of
    width b.

    Three traps, all of which are in the released code:
      1. Manning's n. Check where the engine gets it from. It is NOT the value
         passed into the constructor for Cases 3-6. Report what it actually is.
      2. |u| u, not u^2. Why? What breaks if you use u^2?
      3. R^(4/3) is written in the code as tf.pow(tf.square(R), 2/3). Confirm
         these are the same thing, and say why the author might have written it
         the second way.
    """
    # Trap 1: Manning's n is hard-coded to 0.015 inside the engine's
    #         fun_r_momentum for Cases 3-6; the value passed to the constructor is ignored.
    # Trap 2: |u|u keeps friction opposing the flow when u < 0. With u^2 the friction
    #         term would push reverse flow faster and the solution diverges.
    # Trap 3: (R^2)^(2/3) = R^(4/3) for R > 0; squaring first avoids a fractional
    #         power of a possibly negative intermediate during training.
    n = 0.015
    R = cfg.b * h / (2.0 * h + cfg.b)
    Sf = n * n * np.abs(u) * u / np.power(np.square(R), 2.0 / 3.0)
    return u_t + u * u_x + cfg.g * h_x + cfg.g * (Sf - cfg.slope)


# ===========================================================================
#  Checking harness - you should not need to edit below this line
# ===========================================================================

def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    cases.add_case_argument(p)
    p.add_argument('--variant', default=None)
    p.add_argument('--npoints', type=int, default=2000,
                   help='How many collocation points to check')
    a = p.parse_args()

    if a.case in (1, 2):
        raise SystemExit(
            'Cases 1-2 use the simplified depth-only engine. Use\n'
            '  --case 3  (or your own HEC-RAS case)\n'
            'for this exercise, then repeat the derivation for your own case\n'
            'against engine/SVE_module_dynamic.py by hand in your report.')

    import tensorflow as tf

    cfg = cases.get(a.case)
    variant = a.variant or getattr(cfg, 'variants', ['case%d' % cfg.cid])[0]

    ref = dataprep.load_reference(cfg)
    sets = dataprep.build_training_sets(cfg, ref)
    model = modelbuild.build(cfg, sets, ref, variant=variant, exist_model=2)

    # Pull u, h and all four first derivatives out of the live TF graph.
    #
    # NOTE: the whole collocation set must be fed at once. The engine holds the
    # bed slope as a numpy array with one row per collocation point and
    # subtracts it inside fun_r_momentum, so feeding a subset would trigger a
    # broadcast error. Everything is evaluated, then subsampled afterwards.
    x_s = sets['X_f'][:, 0:1]
    t_s = sets['X_f'][:, 1:2]

    x_tf, t_tf = model.x_f_tf, model.t_f_tf
    u_sym, h_sym = model.net_uh(x_tf, t_tf)
    tensors = dict(
        u=u_sym, h=h_sym,
        u_t=tf.gradients(u_sym, t_tf)[0], u_x=tf.gradients(u_sym, x_tf)[0],
        h_t=tf.gradients(h_sym, t_tf)[0], h_x=tf.gradients(h_sym, x_tf)[0],
        eq1=model.eq1_pred, eq2=model.eq2_pred,
    )
    vals = model.sess.run(tensors, {x_tf: x_s, t_tf: t_s})

    cfg_local = argparse.Namespace(b=cfg.b, slope=np.asarray(sets['slope']),
                                   g=GRAVITY, layers=cfg.layers, cid=cfg.cid)

    print('=' * 74)
    print('CASE %d  variant %s   checking %d collocation points'
          % (cfg.cid, variant, len(x_s)))
    print('=' * 74)
    print('Engine residual magnitudes on the TRAINED model:')
    print('  continuity : mean |eq1| = %.3e   max = %.3e'
          % (np.abs(vals['eq1']).mean(), np.abs(vals['eq1']).max()))
    print('  momentum   : mean |eq2| = %.3e   max = %.3e'
          % (np.abs(vals['eq2']).mean(), np.abs(vals['eq2']).max()))
    print('')

    args = (vals['u'], vals['h'], vals['u_t'], vals['u_x'],
            vals['h_t'], vals['h_x'], cfg_local)

    ok = True
    for name, fn, engine_key in (
            ('continuity', student_mass_residual, 'eq1'),
            ('momentum', student_momentum_residual, 'eq2')):
        try:
            mine = np.asarray(fn(*args)).reshape(-1)
        except NotImplementedError as e:
            print('%-12s NOT IMPLEMENTED (%s)' % (name, e))
            ok = False
            continue
        theirs = vals[engine_key].reshape(-1)
        diff = np.abs(mine - theirs)
        scale = max(np.abs(theirs).max(), 1e-30)
        verdict = 'MATCH' if diff.max() / scale < 1e-5 else 'MISMATCH'
        print('%-12s max abs diff = %.3e   relative = %.3e   -> %s'
              % (name, diff.max(), diff.max() / scale, verdict))
        if verdict == 'MISMATCH':
            ok = False
            worst = int(np.argmax(diff))
            print('             worst point: yours = %.6e  engine = %.6e'
                  % (mine[worst], theirs[worst]))

    dropped = np.abs(vals['h'] * vals['u_x']).reshape(-1)
    kept = np.abs(vals['h_t']).reshape(-1) + np.abs(vals['u'] * vals['h_x']).reshape(-1)
    print('')
    print('Dropped continuity term |h du/dx| on the collocation set:')
    print('  mean = %.3e  median = %.3e  max = %.3e' % (dropped.mean(), np.median(dropped), dropped.max()))
    print('  ratio to retained terms (|h_t|+|u h_x|): mean %.3f  median %.3f'
          % (dropped.mean() / max(kept.mean(), 1e-30), np.median(dropped / np.maximum(kept, 1e-30))))
    print('  engine continuity residual mean |eq1| = %.3e -> dropped term is %.1fx larger'
          % (np.abs(vals['eq1']).mean(), dropped.mean() / max(np.abs(vals['eq1']).mean(), 1e-30)))
    print('')
    if ok:
        print('Both residuals reproduce the engine. Now answer the questions')
        print('in the docstrings above - that is the actual deliverable.')
    else:
        print('Keep working. The equations are in Section 2 of the paper.')


if __name__ == '__main__':
    main()
