    # SigmaOS-screen-saver

    Lock screen & idle screensaver

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/cinnamon-screensaver

    ## Design principles applied
    - **Defensive Programming**
- **Fail-Fast**
- **Least Astonishment**
- **KISS**
- **Separation of Concerns**
- **Deterministic Testing**

    ## Usage
    Verbs: `lock, idle, theme, status`

    ```
    $ sigma-screensaver lock                 # prints the lock plan (dry-run)
$ sigma-screensaver idle --delay 300 --lock on
$ sigma-screensaver theme --list
$ sigma-screensaver status

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).
