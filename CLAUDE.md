- In Atlas the top level object is the Organization. Any given user can create or be a member of multiple organizations. Each user can create mutliple organizations. Within each organization there can  be multiple projects. An organization owner and administrator can create projects. Without each project their can be multiple Clusters. Each Cluster stands alone and represents a container for databases. Each cluster may have one or more users associated with it. Each user at the cluster level has a username and a password.
- when stopping and starting the server use the atlasgui script to start and stop the server
- use inv start and inv stop to start and stop the server processes
- we do not render links fields in the REST API for Atlas as these are used for pagination of data
- keep the pyproject.toml version and the config.py version in sync
- use atlasui start and atlasui stop to start and stop the service
- Keep the two cluster pages in sync as much as possible
- when I say bump the version I always mean by a minor version unless there are breaking changes
- You can only have one M0 cluster per organization
- when I say make a release push everything including tags to github to trigger the release github action
- when we push a tag always make a github release

## Release Process Order
When making a release, follow this exact order:
1. Update documentation
2. Run all tests
3. Bump version in pyproject.toml
4. Commit changes with detailed release notes
5. Create git tag
6. Build Python package locally (uv run python -m build)
7. Build Sphinx documentation locally (cd docs && uv run sphinx-build -b html . _build/html)
8. Push to GitHub (git push && git push --tags)
9. Create GitHub Release with gh release create (this triggers the PyPI publish workflow)
- make sure when we bump the release number that we always make a github release as this ensures that the pypi package gets built
- when starting the atlasui server always specify --port 8100
- fix all test failures in general before making a  release
- when building tests and the UI, always poll for state changes rather than using timeouts. Where an appropriate state change is not available look to create that in the backend.
- pyproject.toml's version is synchronised from the config.py
- use shot-scraper to take screen shots
- always syncrhonize the sphinx documentation version with the pyproject.toml version
- when using shot-scraper for documentation screehshots give the page 5 seconds to load
- we publish to pypi via a github action
- servers started within the development environment should always run on port 8100. All tests should connect to port 8100 by default.