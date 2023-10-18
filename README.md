# homegit

A utility to manage bare git repos in your home directory

See also [Dotfiles: Best way to store in a bare git repository](https://www.atlassian.com/git/tutorials/dotfiles)

## Usage

Once a repo is initialized or cloned, use `homegit` as you would `git`.

### Local repo
```bash
cd $HOME
homegit init
echo "this is a file" > file.txt
homegit add file.txt
homegit commit
homegit log
```

### Remote repo
```bash
homegit clone https://github.com/notwillk/test-homegit.git
cat ~/test_file.txt
```

### Additional repo
```bash
HOMEGIT_REPO=identifier homegit clone https://github.com/notwillk/test-homegit.git
cat ~/test_file.txt
```

### Environment variables
| Variable       | Default value               | Description                                                                                                               |
| -------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| HOME           | *none*.                     | The path to the user's home directory                                                                                     |
| GIT_EXECUTABLE | *the output of `which git`* | The location of the `git` command to execute                                                                              |
| HOMEGIT_DIR    | `$HOME/.homegit`            | The path to the directory containing the [git dir](https://git-scm.com/docs/git#Documentation/git.txt---git-dirltpathgt)s |
| HOMEGIT_REPO   | default                     | The identifier for the source repo                                                                                        |
