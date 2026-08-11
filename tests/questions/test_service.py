from devops_learn.questions.service import QuestionService


def test_asks_nothing_already_known() -> None:
    questions = QuestionService().material_questions(
        environment_known=True,
        public_access_known=True,
        cost_priority_known=True,
        wants_kubernetes_experience=False,
    )
    assert questions == ()


def test_asks_the_kubernetes_reason_only_when_it_was_requested() -> None:
    without = QuestionService().material_questions(
        environment_known=True,
        public_access_known=True,
        cost_priority_known=True,
        wants_kubernetes_experience=False,
    )
    with_learning = QuestionService().material_questions(
        environment_known=True,
        public_access_known=True,
        cost_priority_known=True,
        wants_kubernetes_experience=True,
    )
    assert not any(q.id == "kubernetes_reason" for q in without)
    assert any(q.id == "kubernetes_reason" for q in with_learning)


def test_asks_all_four_when_nothing_is_known() -> None:
    questions = QuestionService().material_questions(
        environment_known=False,
        public_access_known=False,
        cost_priority_known=False,
        wants_kubernetes_experience=True,
    )
    assert len(questions) == 4
