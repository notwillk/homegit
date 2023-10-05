# homegit

## Example usage

### Local repo
`cd $HOME`
`homegit init`
`echo "this is a file" > file.txt`
`homegit git add file.txt`
`homegit git commit`
`homegit git log`

### Remote repo
`homegit clone https://github.com/notwillk/test-homegit.git`
`cat ~/test_file.txt`

### Named repo
`homegit identifier clone https://github.com/notwillk/test-homegit.git`
`cat ~/test_file.txt`
