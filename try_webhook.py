from episode import GitRepo, Episode
import os

repo_addr = 'git@github.com:Windfarer/windfarer.github.io.git'

repo = GitRepo(repo_address=repo_addr)

repo.clone()
os.chdir('repo')
repo.branch('source')
episode = Episode()
episode.build()
repo.branch('master')
# cp files back
repo.add_and_commit()