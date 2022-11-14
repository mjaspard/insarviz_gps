#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# constants #################################################################

DATA_UNIT, SEL_UNIT, PALETTE_UNIT = range(3)  # texture unit use


# common shaders ############################################################

PALETTE_SHADER = r"""
    // handling values
    uniform sampler2D values;

    uniform float v_i; // min and
    uniform float v_a; // max data value to denormalize data

    vec2 v() {
        // compute original value, keep alpha for nans
        vec4 t = texture2D(values, gl_TexCoord[0].st);
        return vec2(t.x*(v_a-v_i)+v_i, t.a);
    }

    // handling palette
    uniform sampler1D palette;

    uniform float v_0; // lower and
    uniform float v_1; // upper bound of data values mapped to the palette

    vec4 colormap(float v) {
        return texture1D(palette, (v-v_0)/(v_1-v_0));
    }
"""


# Map fragment shaders ######################################################

MAP_SHADER = r"""
    uniform sampler2D selection;

    vec2 v();
    vec4 colormap(float v);

    void main() {
        // crop to unit square
        if(
            gl_TexCoord[0].s < 0. || gl_TexCoord[0].s > 1. ||
            gl_TexCoord[0].t < 0. || gl_TexCoord[0].t > 1.
        ) {
            discard;
        }

        // retrieve original value, and color code
        vec2 v = v();
        if(1. - v.y > 1.e-6) { discard; }

        vec4 l = colormap(v.x);
        gl_FragColor = gl_Color * vec4(l.rgb, v.y);

        // handle selection
        vec4 s = texture2D(selection, gl_TexCoord[0].st);
        if(s.a > 0.) {
          gl_FragColor = vec4(1.,0.,0.,1.);
        }
        if(s.a > 2.) {
          gl_FragColor = vec4(1.,1.,1.,1.);
        }
        if(s.a < 0.) {
          gl_FragColor = vec4(0.,1.,0.,1.);
        }

    }
"""


# Minimap fragment shader ###################################################

MINIMAP_SHADER = """
    vec2 v();
    vec4 colormap(float v);

    void main() {
        // retreive original value, and color code
        vec2 v = v();
        if(1. - v.y > 1.e-6) { discard; }
        vec4 l = colormap(v.x);
        gl_FragColor = gl_Color * vec4(l.rgb, v.y);
    }
"""



        # // handle profile subsampling
        # vec4 sub = texture2D(selection, gl_TexCoord[0].st);
        # if(sub.a > 2.) {
        #     gl_FragColor = vec4(1.,1.,1.,1.);
        # }
