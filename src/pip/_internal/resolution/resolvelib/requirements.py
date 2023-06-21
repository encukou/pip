from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name

from pip._internal.req.req_install import InstallRequirement
from pip._internal.req.constructors import install_req_without

from .base import Candidate, CandidateLookup, Requirement, format_name


class ExplicitRequirement(Requirement):
    def __init__(self, candidate: Candidate) -> None:
        self.candidate = candidate

    def __str__(self) -> str:
        return str(self.candidate)

    def __repr__(self) -> str:
        return "{class_name}({candidate!r})".format(
            class_name=self.__class__.__name__,
            candidate=self.candidate,
        )

    @property
    def project_name(self) -> NormalizedName:
        # No need to canonicalize - the candidate did this
        return self.candidate.project_name

    @property
    def name(self) -> str:
        # No need to canonicalize - the candidate did this
        return self.candidate.name

    def format_for_error(self) -> str:
        return self.candidate.format_for_error()

    def get_candidate_lookup(self) -> CandidateLookup:
        return self.candidate, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        return candidate == self.candidate


# TODO: add some comments
class SpecifierRequirement(Requirement):
    # TODO: document additional options
    def __init__(
        self,
        ireq: InstallRequirement,
        *,
        drop_extras: bool = False,
        drop_specifier: bool = False,
    ) -> None:
        assert ireq.link is None, "This is a link, not a specifier"
        self._drop_extras: bool = drop_extras
        self._original_extras = frozenset(ireq.extras)
        # TODO: name
        self._original_req = ireq.req
        self._ireq = install_req_without(
            ireq, without_extras=self._drop_extras, without_specifier=drop_specifier
        )

    def __str__(self) -> str:
        return str(self._original_req)

    def __repr__(self) -> str:
        return "{class_name}({requirement!r})".format(
            class_name=self.__class__.__name__,
            requirement=str(self._ireq.req),
        )

    @property
    def project_name(self) -> NormalizedName:
        assert self._ireq.req, "Specifier-backed ireq is always PEP 508"
        return canonicalize_name(self._ireq.req.name)

    # TODO: make sure this can still be identified for error reporting purposes
    @property
    def name(self) -> str:
        return format_name(
            self.project_name,
            self._original_extras if not self._drop_extras else frozenset(),
        )

    def format_for_error(self) -> str:
        # Convert comma-separated specifiers into "A, B, ..., F and G"
        # This makes the specifier a bit more "human readable", without
        # risking a change in meaning. (Hopefully! Not all edge cases have
        # been checked)
        parts = [s.strip() for s in str(self).split(",")]
        if len(parts) == 0:
            return ""
        elif len(parts) == 1:
            return parts[0]

        return ", ".join(parts[:-1]) + " and " + parts[-1]

    def get_candidate_lookup(self) -> CandidateLookup:
        return None, self._ireq

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        assert candidate.name == self.name, (
            f"Internal issue: Candidate is not for this requirement "
            f"{candidate.name} vs {self.name}"
        )
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        assert self._ireq.req, "Specifier-backed ireq is always PEP 508"
        spec = self._ireq.req.specifier
        return spec.contains(candidate.version, prereleases=True)


class RequiresPythonRequirement(Requirement):
    """A requirement representing Requires-Python metadata."""

    def __init__(self, specifier: SpecifierSet, match: Candidate) -> None:
        self.specifier = specifier
        self._candidate = match

    def __str__(self) -> str:
        return f"Python {self.specifier}"

    def __repr__(self) -> str:
        return "{class_name}({specifier!r})".format(
            class_name=self.__class__.__name__,
            specifier=str(self.specifier),
        )

    @property
    def project_name(self) -> NormalizedName:
        return self._candidate.project_name

    @property
    def name(self) -> str:
        return self._candidate.name

    def format_for_error(self) -> str:
        return str(self)

    def get_candidate_lookup(self) -> CandidateLookup:
        if self.specifier.contains(self._candidate.version, prereleases=True):
            return self._candidate, None
        return None, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        assert candidate.name == self._candidate.name, "Not Python candidate"
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        return self.specifier.contains(candidate.version, prereleases=True)


class UnsatisfiableRequirement(Requirement):
    """A requirement that cannot be satisfied."""

    def __init__(self, name: NormalizedName) -> None:
        self._name = name

    def __str__(self) -> str:
        return f"{self._name} (unavailable)"

    def __repr__(self) -> str:
        return "{class_name}({name!r})".format(
            class_name=self.__class__.__name__,
            name=str(self._name),
        )

    @property
    def project_name(self) -> NormalizedName:
        return self._name

    @property
    def name(self) -> str:
        return self._name

    def format_for_error(self) -> str:
        return str(self)

    def get_candidate_lookup(self) -> CandidateLookup:
        return None, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        return False
